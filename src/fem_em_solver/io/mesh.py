"""Mesh generation utilities for EM simulations."""

from typing import Optional, Tuple, List, Dict
import numpy as np
import gmsh
from mpi4py import MPI
import dolfinx
from dolfinx.io import gmshio


def _interface_facet_tags(
    mesh: "dolfinx.mesh.Mesh",
    cell_tags: "dolfinx.mesh.MeshTags",
    interfaces: Dict[int, Tuple[int, int]],
    existing: Optional["dolfinx.mesh.MeshTags"] = None,
) -> "dolfinx.mesh.MeshTags":
    """Tag the facets shared by two differently-tagged cell regions.

    ``interfaces`` maps a facet tag to the pair of *cell* tags whose common
    facets carry it (order irrelevant). The result merges those facets into
    ``existing``'s tags when one is given.

    Why this is done here and not in gmsh: dim-2 physical groups on facets
    that are **interior** to the partitioned mesh hang ``model_to_mesh`` at
    ``-n 2`` inside ``distribute_entity_data`` (known-issues 9, measured
    2026-08-05; ``-n 1`` completes the identical case in 22.5 s). Cell tags
    distribute fine, and an interface is exactly derivable from them, so the
    interface is reconstructed on the dolfinx side where every rank already
    holds the data it needs.

    Rank-safety: the classification needs the tag of *both* cells behind a
    facet, and one of them is a ghost on a partition-boundary facet. Ghost
    cells are not necessarily carried by ``cell_tags``, so the tag is pushed
    through a DG0 function and ``scatter_forward``ed rather than read from
    ``cell_tags.values`` directly.
    """
    tdim = mesh.topology.dim
    fdim = tdim - 1
    mesh.topology.create_entities(fdim)
    mesh.topology.create_connectivity(fdim, tdim)

    marker_space = dolfinx.fem.functionspace(mesh, ("DG", 0))
    marker = dolfinx.fem.Function(marker_space)
    marker.x.array[:] = 0.0
    cell_to_dof = marker_space.dofmap.list.reshape(-1)
    marker.x.array[cell_to_dof[cell_tags.indices]] = cell_tags.values
    marker.x.scatter_forward()
    cell_value = np.rint(np.real(marker.x.array[cell_to_dof])).astype(np.int32)

    facet_to_cell = mesh.topology.connectivity(fdim, tdim)
    offsets = facet_to_cell.offsets
    links = facet_to_cell.array
    counts = offsets[1:] - offsets[:-1]
    interior = np.flatnonzero(counts == 2)
    side_a = cell_value[links[offsets[interior]]]
    side_b = cell_value[links[offsets[interior] + 1]]

    indices: List[np.ndarray] = []
    values: List[np.ndarray] = []
    if existing is not None and existing.indices.size:
        indices.append(np.asarray(existing.indices, dtype=np.int32))
        values.append(np.asarray(existing.values, dtype=np.int32))

    for facet_tag, (tag_a, tag_b) in sorted(interfaces.items()):
        on_interface = ((side_a == tag_a) & (side_b == tag_b)) | (
            (side_a == tag_b) & (side_b == tag_a)
        )
        found = interior[on_interface]
        indices.append(found.astype(np.int32))
        values.append(np.full(found.size, facet_tag, dtype=np.int32))

    if indices:
        all_indices = np.concatenate(indices)
        all_values = np.concatenate(values)
    else:
        all_indices = np.empty(0, dtype=np.int32)
        all_values = np.empty(0, dtype=np.int32)

    order = np.argsort(all_indices, kind="stable")
    all_indices = all_indices[order]
    all_values = all_values[order]
    if np.unique(all_indices).size != all_indices.size:
        raise RuntimeError(
            "_interface_facet_tags: a facet was claimed by more than one tag; "
            f"{all_indices.size} entries, {np.unique(all_indices).size} unique"
        )
    return dolfinx.mesh.meshtags(mesh, fdim, all_indices, all_values)


class MeshGenerator:
    """Generate meshes for common geometries using Gmsh."""

    @staticmethod
    def straight_wire_domain(
        wire_length: float = 1.0,
        wire_radius: float = 0.001,
        domain_radius: float = 0.1,
        resolution: float = 0.005,
        comm: MPI.Intracomm = MPI.COMM_WORLD,
        rank: int = 0
    ) -> Tuple[dolfinx.mesh.Mesh, dolfinx.mesh.MeshTags, dolfinx.mesh.MeshTags]:
        """Generate mesh for straight wire in cylindrical domain.
        
        Creates a cylindrical domain with a thin wire along the z-axis.
        Useful for validating against the analytical solution for an
        infinite straight wire.
        
        Parameters
        ----------
        wire_length : float
            Length of wire [m]
        wire_radius : float
            Radius of wire [m] (should be small for thin wire approximation)
        domain_radius : float
            Radius of surrounding cylindrical domain [m]
        resolution : float
            Characteristic mesh size [m]
        comm : MPI.Intracomm
            MPI communicator
        rank : int
            Rank for Gmsh model (usually 0)
            
        Returns
        -------
        mesh : dolfinx.mesh.Mesh
            The generated mesh
        cell_tags : dolfinx.mesh.MeshTags
            Cell tags for subdomains (wire, surrounding)
        facet_tags : dolfinx.mesh.MeshTags
            Facet tags for boundaries
        """
        if comm.rank == rank:
            # Initialize Gmsh
            gmsh.initialize()
            gmsh.model.add("straight_wire")
            
            # Create wire (cylinder along z-axis)
            wire_tag = gmsh.model.occ.addCylinder(
                0, 0, -wire_length/2,  # center of bottom face
                0, 0, wire_length,      # axis direction and height
                wire_radius
            )
            
            # Create surrounding domain (hollow cylinder)
            domain_tag = gmsh.model.occ.addCylinder(
                0, 0, -wire_length/2,
                0, 0, wire_length,
                domain_radius
            )
            
            # Cut wire out of domain to create separate volumes
            # Actually, we want both as separate volumes, so we fragment
            ov, ovv = gmsh.model.occ.fragment(
                [(3, domain_tag)],
                [(3, wire_tag)]
            )
            gmsh.model.occ.synchronize()
            
            # Get volumes
            volumes = gmsh.model.getEntities(dim=3)
            wire_volume = None
            domain_volume = None
            
            # Tag volumes based on their bounding box
            for vol in volumes:
                bbox = gmsh.model.getBoundingBox(vol[0], vol[1])
                # Check if this is the wire (small radius)
                x_min, y_min, z_min, x_max, y_max, z_max = bbox
                r_max = np.sqrt(max(x_max**2, y_max**2))
                if r_max < 2 * wire_radius:
                    wire_volume = vol[1]
                else:
                    domain_volume = vol[1]
            
            # Add physical groups
            if wire_volume:
                gmsh.model.addPhysicalGroup(3, [wire_volume], tag=1)
                gmsh.model.setPhysicalName(3, 1, "wire")
            
            if domain_volume:
                gmsh.model.addPhysicalGroup(3, [domain_volume], tag=2)
                gmsh.model.setPhysicalName(3, 2, "domain")
            
            # Tag boundaries
            surfaces = gmsh.model.getEntities(dim=2)
            boundary_surfaces = []
            wire_surfaces = []
            
            for surf in surfaces:
                bbox = gmsh.model.getBoundingBox(surf[0], surf[1])
                x_min, y_min, z_min, x_max, y_max, z_max = bbox
                r_max = np.sqrt(max(x_max**2, y_max**2))
                
                # Cylindrical boundary of domain
                if abs(r_max - domain_radius) < resolution:
                    boundary_surfaces.append(surf[1])
                # Wire surface
                elif r_max < 2 * wire_radius:
                    wire_surfaces.append(surf[1])
            
            if boundary_surfaces:
                gmsh.model.addPhysicalGroup(2, boundary_surfaces, tag=1)
                gmsh.model.setPhysicalName(2, 1, "boundary")
            
            if wire_surfaces:
                gmsh.model.addPhysicalGroup(2, wire_surfaces, tag=2)
                gmsh.model.setPhysicalName(2, 2, "wire_surface")
            
            # Set mesh size
            gmsh.model.mesh.setSize(gmsh.model.getEntities(0), resolution)
            
            # Generate mesh
            gmsh.model.mesh.generate(3)
            gmsh.model.mesh.optimize("Netgen")

        # Convert to dolfinx mesh
        mesh, cell_tags, facet_tags = gmshio.model_to_mesh(
            gmsh.model, comm, rank, gdim=3
        )
        
        if comm.rank == rank:
            gmsh.finalize()
        
        return mesh, cell_tags, facet_tags
    
    @staticmethod
    def circular_loop_domain(
        loop_radius: float = 0.05,
        wire_radius: float = 0.001,
        domain_radius: float = 0.15,
        resolution: float = 0.005,
        comm: MPI.Intracomm = MPI.COMM_WORLD,
        rank: int = 0
    ) -> Tuple[dolfinx.mesh.Mesh, dolfinx.mesh.MeshTags, dolfinx.mesh.MeshTags]:
        """Generate mesh for circular current loop in spherical domain.
        
        Creates a torus (ring) for the wire surrounded by a spherical air domain.
        The loop lies in the xy-plane centered at origin.
        
        Parameters
        ----------
        loop_radius : float
            Major radius of loop (distance from center to wire center) [m]
        wire_radius : float
            Minor radius of wire cross-section [m]
        domain_radius : float
            Radius of surrounding spherical domain [m]
        resolution : float
            Characteristic mesh size [m]
        comm : MPI.Intracomm
            MPI communicator
        rank : int
            Rank for Gmsh model (usually 0)
            
        Returns
        -------
        mesh : dolfinx.mesh.Mesh
            The generated mesh
        cell_tags : dolfinx.mesh.MeshTags
            Cell tags for subdomains (wire=1, air=2)
        facet_tags : dolfinx.mesh.MeshTags
            Facet tags for boundaries
        """
        if comm.rank == rank:
            # Initialize Gmsh
            gmsh.initialize()
            gmsh.model.add("circular_loop")
            
            # Create wire as torus in xy-plane
            # addTorus(x, y, z, major_radius, minor_radius)
            wire_tag = gmsh.model.occ.addTorus(0, 0, 0, loop_radius, wire_radius)
            
            # Create surrounding spherical domain
            domain_tag = gmsh.model.occ.addSphere(0, 0, 0, domain_radius)
            
            # Fragment to get separate volumes
            ov, ovv = gmsh.model.occ.fragment(
                [(3, domain_tag)],
                [(3, wire_tag)]
            )
            gmsh.model.occ.synchronize()
            
            # Get volumes and tag them
            volumes = gmsh.model.getEntities(dim=3)
            wire_volume = None
            air_volume = None
            
            for vol in volumes:
                bbox = gmsh.model.getBoundingBox(vol[0], vol[1])
                x_min, y_min, z_min, x_max, y_max, z_max = bbox
                
                # Compute bounding box dimensions
                dx = x_max - x_min
                dy = y_max - y_min
                dz = z_max - z_min
                
                # Wire has smaller bounding box
                max_dim = max(dx, dy, dz)
                if max_dim < 4 * loop_radius:  # Wire is smaller
                    wire_volume = vol[1]
                else:
                    air_volume = vol[1]
            
            # Add physical groups
            if wire_volume:
                gmsh.model.addPhysicalGroup(3, [wire_volume], tag=1)
                gmsh.model.setPhysicalName(3, 1, "wire")
            
            if air_volume:
                gmsh.model.addPhysicalGroup(3, [air_volume], tag=2)
                gmsh.model.setPhysicalName(3, 2, "air")
            
            # Tag boundaries
            surfaces = gmsh.model.getEntities(dim=2)
            boundary_surfaces = []
            
            for surf in surfaces:
                bbox = gmsh.model.getBoundingBox(surf[0], surf[1])
                x_min, y_min, z_min, x_max, y_max, z_max = bbox
                
                # Check if on outer spherical boundary
                r_max = np.sqrt(x_max**2 + y_max**2 + z_max**2)
                if abs(r_max - domain_radius) < resolution:
                    boundary_surfaces.append(surf[1])
            
            if boundary_surfaces:
                gmsh.model.addPhysicalGroup(2, boundary_surfaces, tag=1)
                gmsh.model.setPhysicalName(2, 1, "outer_boundary")
            
            # Set mesh size
            gmsh.model.mesh.setSize(gmsh.model.getEntities(0), resolution)
            
            # Generate mesh
            gmsh.model.mesh.generate(3)
            gmsh.model.mesh.optimize("Netgen")
            
        # Convert to dolfinx mesh
        mesh, cell_tags, facet_tags = gmshio.model_to_mesh(
            gmsh.model, comm, rank, gdim=3
        )
        
        if comm.rank == rank:
            gmsh.finalize()
        
        return mesh, cell_tags, facet_tags
    
    @staticmethod
    def helmholtz_coil_domain(
        loop_radius: float = 0.05,
        wire_radius: float = 0.002,  # Increased from 0.001 for simpler mesh
        domain_radius: float = 0.12,  # Reduced from 0.15
        resolution: float = 0.008,    # Coarser mesh
        comm: MPI.Intracomm = MPI.COMM_WORLD,
        rank: int = 0
    ) -> Tuple[dolfinx.mesh.Mesh, dolfinx.mesh.MeshTags, dolfinx.mesh.MeshTags]:
        """Generate mesh for Helmholtz coil in spherical domain.
        
        A Helmholtz coil consists of two identical circular loops separated
        by a distance equal to their radius. This configuration creates a
        highly uniform magnetic field in the central region.
        
        The loops are positioned at z = -R/2 and z = +R/2, where R is the
        loop radius.
        
        Parameters
        ----------
        loop_radius : float
            Major radius of each loop (distance from center to wire center) [m]
        wire_radius : float
            Minor radius of wire cross-section [m]
        domain_radius : float
            Radius of surrounding spherical domain [m]
        resolution : float
            Characteristic mesh size [m]
        comm : MPI.Intracomm
            MPI communicator
        rank : int
            Rank for Gmsh model (usually 0)
            
        Returns
        -------
        mesh : dolfinx.mesh.Mesh
            The generated mesh
        cell_tags : dolfinx.mesh.MeshTags
            Cell tags for subdomains (wire=1, air=2)
        facet_tags : dolfinx.mesh.MeshTags
            Facet tags for boundaries
        """
        if comm.rank == rank:
            # Initialize Gmsh
            gmsh.initialize()
            gmsh.model.add("helmholtz_coil")
            
            # Helmholtz condition: separation = loop radius
            separation = loop_radius
            z1 = -separation / 2
            z2 = separation / 2
            
            # Create two wire tori at z = -R/2 and z = +R/2
            # addTorus(x, y, z, major_radius, minor_radius)
            wire1_tag = gmsh.model.occ.addTorus(0, 0, z1, loop_radius, wire_radius)
            wire2_tag = gmsh.model.occ.addTorus(0, 0, z2, loop_radius, wire_radius)
            
            # Create surrounding spherical domain
            domain_tag = gmsh.model.occ.addSphere(0, 0, 0, domain_radius)
            
            # Fragment to get separate volumes
            # First fragment domain with wire1
            ov1, ovv1 = gmsh.model.occ.fragment(
                [(3, domain_tag)],
                [(3, wire1_tag)]
            )
            gmsh.model.occ.synchronize()
            
            # Then fragment result with wire2
            # Get the air volume from previous fragmentation
            volumes_after_first = gmsh.model.getEntities(dim=3)
            air_tag = None
            wire1_volume = None
            for vol in volumes_after_first:
                bbox = gmsh.model.getBoundingBox(vol[0], vol[1])
                x_min, y_min, z_min, x_max, y_max, z_max = bbox
                max_dim = max(x_max - x_min, y_max - y_min, z_max - z_min)
                # Wire is smaller than air domain
                if max_dim < 4 * loop_radius:
                    wire1_volume = vol[1]
                else:
                    air_tag = vol[1]
            
            # Fragment air with second wire
            if air_tag:
                ov2, ovv2 = gmsh.model.occ.fragment(
                    [(3, air_tag)],
                    [(3, wire2_tag)]
                )
            gmsh.model.occ.synchronize()
            
            # Get final volumes and tag them
            volumes = gmsh.model.getEntities(dim=3)
            wire_volumes = []
            air_volume = None
            
            for vol in volumes:
                bbox = gmsh.model.getBoundingBox(vol[0], vol[1])
                x_min, y_min, z_min, x_max, y_max, z_max = bbox
                
                # Compute bounding box dimensions
                dx = x_max - x_min
                dy = y_max - y_min
                dz = z_max - z_min
                max_dim = max(dx, dy, dz)
                
                # Wire volumes are smaller and have z-extent ~ 2*wire_radius
                if max_dim < 4 * loop_radius and dz < 4 * wire_radius:
                    wire_volumes.append(vol[1])
                else:
                    air_volume = vol[1]
            
            # Add physical groups
            if wire_volumes:
                # Tag both wires as "wire" (tag=1)
                gmsh.model.addPhysicalGroup(3, wire_volumes, tag=1)
                gmsh.model.setPhysicalName(3, 1, "wire")
            
            if air_volume:
                gmsh.model.addPhysicalGroup(3, [air_volume], tag=2)
                gmsh.model.setPhysicalName(3, 2, "air")
            
            # Tag outer boundary
            surfaces = gmsh.model.getEntities(dim=2)
            boundary_surfaces = []
            
            for surf in surfaces:
                bbox = gmsh.model.getBoundingBox(surf[0], surf[1])
                x_min, y_min, z_min, x_max, y_max, z_max = bbox
                
                # Check if on outer spherical boundary
                r_max = np.sqrt(x_max**2 + y_max**2 + z_max**2)
                if abs(r_max - domain_radius) < resolution:
                    boundary_surfaces.append(surf[1])
            
            if boundary_surfaces:
                gmsh.model.addPhysicalGroup(2, boundary_surfaces, tag=1)
                gmsh.model.setPhysicalName(2, 1, "outer_boundary")
            
            # Set mesh size
            gmsh.model.mesh.setSize(gmsh.model.getEntities(0), resolution)
            
            # Generate mesh
            gmsh.model.mesh.generate(3)
            # Skip optimization for Helmholtz coil to avoid Gmsh hangs
            # gmsh.model.mesh.optimize("Netgen")
            
        # Convert to dolfinx mesh
        mesh, cell_tags, facet_tags = gmshio.model_to_mesh(
            gmsh.model, comm, rank, gdim=3
        )
        
        if comm.rank == rank:
            gmsh.finalize()
        
        return mesh, cell_tags, facet_tags
    
    @staticmethod
    def rectangular_domain(
        bounds: Tuple[float, float, float, float, float, float],
        resolution: float,
        comm: MPI.Intracomm = MPI.COMM_WORLD,
        rank: int = 0
    ) -> dolfinx.mesh.Mesh:
        """Generate simple rectangular domain.
        
        Parameters
        ----------
        bounds : tuple
            (xmin, xmax, ymin, ymax, zmin, zmax)
        resolution : float
            Mesh size
        comm : MPI.Intracomm
            MPI communicator
        rank : int
            Rank for Gmsh
            
        Returns
        -------
        mesh : dolfinx.mesh.Mesh
            The generated mesh
        """
        if comm.rank == rank:
            gmsh.initialize()
            gmsh.model.add("rectangular")
            
            xmin, xmax, ymin, ymax, zmin, zmax = bounds
            
            # Create box
            box = gmsh.model.occ.addBox(xmin, ymin, zmin, 
                                         xmax-xmin, ymax-ymin, zmax-zmin)
            gmsh.model.occ.synchronize()
            
            gmsh.model.addPhysicalGroup(3, [box], tag=1)
            
            # Set mesh size
            gmsh.model.mesh.setSize(gmsh.model.getEntities(0), resolution)
            gmsh.model.mesh.generate(3)
        
        mesh, _, _ = gmshio.model_to_mesh(gmsh.model, comm, rank, gdim=3)
        
        if comm.rank == rank:
            gmsh.finalize()
        
        return mesh
    
    @staticmethod
    def create_simple_box(
        L: float = 1.0,
        n: int = 10,
        comm: MPI.Intracomm = MPI.COMM_WORLD
    ) -> dolfinx.mesh.Mesh:
        """Create simple box mesh using dolfinx built-in generator.
        
        Parameters
        ----------
        L : float
            Box half-length (domain is [-L, L]³)
        n : int
            Number of cells in each direction
        comm : MPI.Intracomm
            MPI communicator
            
        Returns
        -------
        mesh : dolfinx.mesh.Mesh
            Box mesh
        """
        from dolfinx.mesh import create_box, CellType
        
        domain = [(-L, -L, -L), (L, L, L)]
        mesh = create_box(comm, domain, [n, n, n], CellType.tetrahedron)
        
        return mesh
    
    @staticmethod
    def cylindrical_domain(
        inner_radius: float = 0.01,
        outer_radius: float = 0.1,
        length: float = 0.2,
        resolution: float = 0.02,
        comm: MPI.Intracomm = MPI.COMM_WORLD,
        rank: int = 0
    ) -> Tuple[dolfinx.mesh.Mesh, dolfinx.mesh.MeshTags, dolfinx.mesh.MeshTags]:
        """Generate mesh with cylindrical inner volume inside cylindrical domain.
        
        Creates two concentric cylinders along the z-axis. Useful for practicing
        multi-volume meshing and for problems with cylindrical symmetry.
        
        Parameters
        ----------
        inner_radius : float
            Radius of inner cylinder [m]
        outer_radius : float
            Radius of outer cylinder [m]
        length : float
            Length of cylinders along z-axis [m]
        resolution : float
            Characteristic mesh size [m]
        comm : MPI.Intracomm
            MPI communicator
        rank : int
            Rank for Gmsh model (usually 0)
            
        Returns
        -------
        mesh : dolfinx.mesh.Mesh
            The generated mesh
        cell_tags : dolfinx.mesh.MeshTags
            Cell tags for subdomains (inner=1, outer=2)
        facet_tags : dolfinx.mesh.MeshTags
            Facet tags for boundaries
        """
        if comm.rank == rank:
            # Initialize Gmsh
            gmsh.initialize()
            gmsh.model.add("cylindrical_domain")
            
            # Create inner cylinder along z-axis
            inner_tag = gmsh.model.occ.addCylinder(
                0, 0, -length/2,  # center of bottom face
                0, 0, length,      # axis direction and height
                inner_radius
            )
            
            # Create outer cylinder
            outer_tag = gmsh.model.occ.addCylinder(
                0, 0, -length/2,
                0, 0, length,
                outer_radius
            )
            
            # Fragment to create separate volumes (inner and outer region)
            ov, ovv = gmsh.model.occ.fragment(
                [(3, outer_tag)],
                [(3, inner_tag)]
            )
            gmsh.model.occ.synchronize()
            
            # Get volumes and tag them
            volumes = gmsh.model.getEntities(dim=3)
            inner_volume = None
            outer_volume = None
            
            for vol in volumes:
                bbox = gmsh.model.getBoundingBox(vol[0], vol[1])
                x_min, y_min, z_min, x_max, y_max, z_max = bbox
                
                # Check if this is the inner cylinder by radius
                r_max = np.sqrt(max(x_max**2, y_max**2))
                if r_max < (inner_radius + outer_radius) / 2:
                    inner_volume = vol[1]
                else:
                    outer_volume = vol[1]
            
            # Add physical groups
            if inner_volume:
                gmsh.model.addPhysicalGroup(3, [inner_volume], tag=1)
                gmsh.model.setPhysicalName(3, 1, "inner")
            
            if outer_volume:
                gmsh.model.addPhysicalGroup(3, [outer_volume], tag=2)
                gmsh.model.setPhysicalName(3, 2, "outer")
            
            # Tag boundaries
            surfaces = gmsh.model.getEntities(dim=2)
            outer_boundary_surfaces = []
            inner_boundary_surfaces = []
            
            for surf in surfaces:
                bbox = gmsh.model.getBoundingBox(surf[0], surf[1])
                x_min, y_min, z_min, x_max, y_max, z_max = bbox
                r_max = np.sqrt(max(x_max**2, y_max**2))
                
                # Outer cylindrical boundary
                if abs(r_max - outer_radius) < resolution:
                    outer_boundary_surfaces.append(surf[1])
                # Inner cylinder surface
                elif abs(r_max - inner_radius) < resolution:
                    inner_boundary_surfaces.append(surf[1])
            
            if outer_boundary_surfaces:
                gmsh.model.addPhysicalGroup(2, outer_boundary_surfaces, tag=1)
                gmsh.model.setPhysicalName(2, 1, "outer_boundary")
            
            if inner_boundary_surfaces:
                gmsh.model.addPhysicalGroup(2, inner_boundary_surfaces, tag=2)
                gmsh.model.setPhysicalName(2, 2, "inner_boundary")
            
            # Set mesh size
            gmsh.model.mesh.setSize(gmsh.model.getEntities(0), resolution)
            
            # Generate mesh
            gmsh.model.mesh.generate(3)
            gmsh.model.mesh.optimize("Netgen")
            
        # Convert to dolfinx mesh
        mesh, cell_tags, facet_tags = gmshio.model_to_mesh(
            gmsh.model, comm, rank, gdim=3
        )
        
        if comm.rank == rank:
            gmsh.finalize()
        
        return mesh, cell_tags, facet_tags

    @staticmethod
    def two_cylinder_domain(
        separation: float = 0.05,
        radius: float = 0.01,
        length: float = 0.1,
        resolution: float = 0.02,
        comm: MPI.Intracomm = MPI.COMM_WORLD,
        rank: int = 0
    ) -> Tuple[dolfinx.mesh.Mesh, dolfinx.mesh.MeshTags, dolfinx.mesh.MeshTags]:
        """Generate mesh with two side-by-side cylinders inside a box domain.

        This intentionally avoids boolean operations/fragmentation and keeps
        all three volumes explicitly tagged.

        Parameters
        ----------
        separation : float
            Center-to-center distance between the two cylinders [m]
        radius : float
            Radius of each cylinder [m]
        length : float
            Cylinder length along z-axis [m]
        resolution : float
            Characteristic mesh size [m]
        comm : MPI.Intracomm
            MPI communicator
        rank : int
            Rank for Gmsh model (usually 0)

        Returns
        -------
        mesh : dolfinx.mesh.Mesh
            The generated mesh
        cell_tags : dolfinx.mesh.MeshTags
            Cell tags for subdomains (cylinder_1=1, cylinder_2=2, domain=3)
        facet_tags : dolfinx.mesh.MeshTags
            Facet tags for boundaries
        """
        if comm.rank == rank:
            gmsh.initialize()
            gmsh.model.add("two_cylinder_domain")

            x_offset = separation / 2

            cylinder_1 = gmsh.model.occ.addCylinder(
                -x_offset, 0, -length / 2,
                0, 0, length,
                radius
            )
            cylinder_2 = gmsh.model.occ.addCylinder(
                x_offset, 0, -length / 2,
                0, 0, length,
                radius
            )

            box_half_x = x_offset + 2.0 * radius
            box_half_y = 2.0 * radius
            domain = gmsh.model.occ.addBox(
                -box_half_x,
                -box_half_y,
                -length / 2,
                2.0 * box_half_x,
                2.0 * box_half_y,
                length,
            )

            gmsh.model.occ.synchronize()

            gmsh.model.addPhysicalGroup(3, [cylinder_1], tag=1)
            gmsh.model.setPhysicalName(3, 1, "cylinder_1")

            gmsh.model.addPhysicalGroup(3, [cylinder_2], tag=2)
            gmsh.model.setPhysicalName(3, 2, "cylinder_2")

            gmsh.model.addPhysicalGroup(3, [domain], tag=3)
            gmsh.model.setPhysicalName(3, 3, "domain")

            # Tag all box boundary surfaces as outer boundary
            boundary_surfaces = []
            x_tol = box_half_x + resolution
            y_tol = box_half_y + resolution
            z_tol = (length / 2) + resolution

            for dim, surf in gmsh.model.getEntities(dim=2):
                x_min, y_min, z_min, x_max, y_max, z_max = gmsh.model.getBoundingBox(dim, surf)
                if (
                    abs(abs(x_min) - box_half_x) < x_tol or abs(abs(x_max) - box_half_x) < x_tol
                    or abs(abs(y_min) - box_half_y) < y_tol or abs(abs(y_max) - box_half_y) < y_tol
                    or abs(abs(z_min) - (length / 2)) < z_tol or abs(abs(z_max) - (length / 2)) < z_tol
                ):
                    boundary_surfaces.append(surf)

            if boundary_surfaces:
                gmsh.model.addPhysicalGroup(2, boundary_surfaces, tag=1)
                gmsh.model.setPhysicalName(2, 1, "outer_boundary")

            gmsh.model.mesh.setSize(gmsh.model.getEntities(0), resolution)
            gmsh.model.mesh.generate(3)
            gmsh.model.mesh.optimize("Netgen")

        mesh, cell_tags, facet_tags = gmshio.model_to_mesh(
            gmsh.model, comm, rank, gdim=3
        )

        if comm.rank == rank:
            gmsh.finalize()

        return mesh, cell_tags, facet_tags

    @staticmethod
    def two_torus_domain(
        separation: float = 0.05,
        major_radius: float = 0.02,
        minor_radius: float = 0.005,
        resolution: float = 0.02,
        comm: MPI.Intracomm = MPI.COMM_WORLD,
        rank: int = 0,
        *,
        air_padding: Optional[float] = None,
        wire_resolution: Optional[float] = None,
        far_resolution: Optional[float] = None,
        port_gap: bool = False,
        gap_angle: float = 0.30,
        gap_clearance: float = 1.0e-3,
    ) -> Tuple[dolfinx.mesh.Mesh, dolfinx.mesh.MeshTags, dolfinx.mesh.MeshTags]:
        """Generate mesh with two tori inside a box domain.

        The box is ``occ.fragment``-ed against both tori, so the three volumes
        share conforming interfaces and the mesh is a single connected
        component. Cell tags: ``1`` wire 1 (``z < 0``), ``2`` wire 2
        (``z > 0``), ``3`` the air box minus the two tori. Facet tag ``1`` is
        the outer boundary.

        With ``port_gap=True`` each torus additionally carries a lumped-port
        gap (``PORT-1`` step 3b-i): the torus becomes a partial torus of
        opening ``2*pi - gap_angle`` centred on the ``+x`` axis, and a
        rectangular gap box bridges the two arc ends, tagged ``101`` (wire 1)
        and ``102`` (wire 2). Default is **off**, so every existing caller
        meshes exactly as before.

        This fixture is partitioned with ``GhostMode.shared_facet`` (unlike
        the rest of `io/mesh.py`, which takes gmshio's ghost-free default):
        the port facets are interior, so both the tag reconstruction and any
        ``dS`` integral over them need the cell on the far side of a
        partition-boundary facet. See :func:`_interface_facet_tags` and
        known-issues 9.

        Until 2026-08-01 this fixture added the volumes without fragmenting
        (`GEO-8`): gmsh then meshed the box *solid* through the torus regions
        and the tori as two disconnected islands, so a source restricted to a
        torus tag produced no field in the air (``PORT-1`` measured
        ``Z12 == 0``). Do not remove the fragment call.

        Parameters
        ----------
        air_padding:
            Clearance between the coil envelope and the outer box [m]. When
            ``None`` (default) this is ``2 * minor_radius``, which preserves the
            historical box size but couples the air gap to the wire radius --
            making the wire thinner shrinks the air box.

            That coupling matters physically. The outer boundary carries the
            natural condition ``n x (mu^-1 curl A) = 0``, i.e. ``n x H = 0``,
            which behaves as a perfect *magnetic* conductor and mirrors flux
            back into the domain, inflating the on-axis field. Measured centre-
            field error against the analytic Helmholtz solution:

                box half-width 1.45R -> 43.7%
                box half-width 1.75R -> 20.5%   (historical default)
                box half-width 2.50R ->  4.4%

            For free-space comparisons pass ``air_padding >= 2 * major_radius``.
        wire_resolution:
            Target mesh size on the torus surfaces [m]. When ``None``, a single
            uniform size (``resolution``) is used everywhere, as before. Setting
            this enables graded refinement so a large air box stays affordable:
            cell count is otherwise driven by the box volume, not the wire.
        far_resolution:
            Target mesh size at the outer boundary [m]. Defaults to
            ``resolution`` when grading is enabled.
        port_gap:
            Opt in to the gapped (lumped-port) variant. Default ``False``
            reproduces the ungapped fixture byte for byte.
        gap_angle:
            Angular opening of the removed wedge [rad], centred on ``+x``.
        gap_clearance:
            Margin by which the gap box overhangs the conductor tube [m]. It
            sets the box's radial and axial half-size (``minor_radius +
            gap_clearance``) and how far the box buries into each arc end.
        """
        if comm.rank == rank:
            gmsh.initialize()
            gmsh.model.add("two_torus_domain")

            z_offset = separation / 2

            if port_gap:
                if not 0.0 < gap_angle < np.pi:
                    raise ValueError(
                        f"gap_angle must be in (0, pi), got {gap_angle!r}"
                    )
                if gap_clearance <= 0.0:
                    raise ValueError(
                        f"gap_clearance must be positive, got {gap_clearance!r}"
                    )
                # Partial torus: OCC sweeps from phi = 0 to phi = angle, so
                # rotating by +gap_angle/2 leaves the wedge centred on +x.
                wire_1 = gmsh.model.occ.addTorus(
                    0, 0, -z_offset, major_radius, minor_radius,
                    angle=2.0 * np.pi - gap_angle,
                )
                wire_2 = gmsh.model.occ.addTorus(
                    0, 0, z_offset, major_radius, minor_radius,
                    angle=2.0 * np.pi - gap_angle,
                )
                for wire in (wire_1, wire_2):
                    gmsh.model.occ.rotate(
                        [(3, wire)], 0, 0, 0, 0, 0, 1, 0.5 * gap_angle
                    )
                # The box must *cross* both arc ends, not stop short of them:
                # a box face flush with a tilted arc end is not constructible
                # (the two end planes meet at gap_angle), so the box buries
                # `gap_clearance` past the end-face centres and the gap group
                # takes precedence over the conductor below. That makes the
                # gap the box exactly -- planar faces, meshed to roundoff --
                # and the conductor the arc minus what the box swallowed.
                gap_half_xz = minor_radius + gap_clearance
                gap_half_y = major_radius * np.sin(0.5 * gap_angle) + gap_clearance
                gap_size = (2.0 * gap_half_xz, 2.0 * gap_half_y, 2.0 * gap_half_xz)
                gap_1 = gmsh.model.occ.addBox(
                    major_radius - gap_half_xz,
                    -gap_half_y,
                    -z_offset - gap_half_xz,
                    *gap_size,
                )
                gap_2 = gmsh.model.occ.addBox(
                    major_radius - gap_half_xz,
                    -gap_half_y,
                    z_offset - gap_half_xz,
                    *gap_size,
                )
            else:
                wire_1 = gmsh.model.occ.addTorus(0, 0, -z_offset, major_radius, minor_radius)
                wire_2 = gmsh.model.occ.addTorus(0, 0, z_offset, major_radius, minor_radius)

            padding = 2.0 * minor_radius if air_padding is None else float(air_padding)
            if padding <= 0.0:
                raise ValueError(f"air_padding must be positive, got {padding!r}")

            radial_extent = major_radius + minor_radius
            box_half_x = radial_extent + padding
            box_half_y = radial_extent + padding
            box_half_z = z_offset + minor_radius + padding

            domain = gmsh.model.occ.addBox(
                -box_half_x,
                -box_half_y,
                -box_half_z,
                2.0 * box_half_x,
                2.0 * box_half_y,
                2.0 * box_half_z,
            )

            tool_tags = [wire_1, wire_2]
            if port_gap:
                tool_tags += [gap_1, gap_2]
            _, fragment_map = gmsh.model.occ.fragment(
                [(3, domain)], [(3, tag) for tag in tool_tags]
            )
            gmsh.model.occ.synchronize()

            if port_gap:
                # Groups re-derived from the fragment out-map (`GEO-9` step 2b
                # machinery): fragment renumbers, so absolute tags from before
                # the call mean nothing after it. The out-map is positional,
                # objects first then tools.
                input_tags = [domain] + tool_tags
                if len(fragment_map) != len(input_tags):
                    raise RuntimeError(
                        "two_torus_domain: occ.fragment returned an out-map of "
                        f"{len(fragment_map)} entries for {len(input_tags)} inputs"
                    )
                ancestors: Dict[int, set] = {}
                for input_tag, pieces in zip(input_tags, fragment_map):
                    for dim, piece in pieces:
                        if dim == 3:
                            ancestors.setdefault(piece, set()).add(input_tag)

                wire_of = {wire_1: 1, wire_2: 2}
                gap_of = {gap_1: 101, gap_2: 102}
                group_of_piece: Dict[int, int] = {}
                for piece, sources in ancestors.items():
                    # Gap wins over metal: the box IS the dielectric gap, and
                    # its exact volume is what the step-3b-i anchor measures.
                    hit_gap = sources & gap_of.keys()
                    hit_wire = sources & wire_of.keys()
                    if hit_gap:
                        group_of_piece[piece] = min(gap_of[t] for t in hit_gap)
                    elif hit_wire:
                        group_of_piece[piece] = min(wire_of[t] for t in hit_wire)
                    else:
                        group_of_piece[piece] = 3

                pieces_by_group: Dict[int, List[int]] = {}
                for piece, group in sorted(group_of_piece.items()):
                    pieces_by_group.setdefault(group, []).append(piece)

                group_names = {1: "wire_1", 2: "wire_2", 3: "domain",
                               101: "gap_1", 102: "gap_2"}
                volumes = gmsh.model.getEntities(dim=3)
                masses = {tag: gmsh.model.occ.getMass(3, tag) for _, tag in volumes}
                missing = [group_names[g] for g in (1, 2, 3, 101, 102)
                           if g not in pieces_by_group]
                if missing:
                    raise RuntimeError(
                        "two_torus_domain: occ.fragment left no piece for "
                        f"{', '.join(missing)}; {len(volumes)} volumes, "
                        "per-volume masses [m^3]: "
                        + ", ".join(f"tag {t}: {m:.6e}" for t, m in sorted(masses.items()))
                    )

                for group, pieces in sorted(pieces_by_group.items()):
                    gmsh.model.addPhysicalGroup(3, pieces, tag=group)
                    gmsh.model.setPhysicalName(3, group, group_names[group])

                # Every 3-D entity must carry a marker; a cell with none is
                # what `gmshio.py:118` asserts on. Checked against the model,
                # not the out-map, so an unmentioned piece cannot hide.
                grouped_volumes = set()
                for _, group_tag in gmsh.model.getPhysicalGroups(dim=3):
                    grouped_volumes.update(
                        gmsh.model.getEntitiesForPhysicalGroup(3, group_tag)
                    )
                ungrouped = sorted({tag for _, tag in volumes} - grouped_volumes)
                if ungrouped:
                    raise RuntimeError(
                        "two_torus_domain: 3-D entities carry no physical group: "
                        f"{ungrouped}; {len(volumes)} volumes, masses [m^3]: "
                        + ", ".join(f"tag {t}: {masses[t]:.6e}" for t in ungrouped)
                    )

                print(
                    f"[two-torus-mesh] gapped fragment volumes={len(volumes)} "
                    + " ".join(
                        f"{group_names[g]}={sum(masses[p] for p in pieces):.6e}"
                        f"({len(pieces)}p)"
                        for g, pieces in sorted(pieces_by_group.items())
                    )
                    + f" gap_box_analytic={gap_size[0] * gap_size[1] * gap_size[2]:.6e}",
                    flush=True,
                )

                wire_volumes = {1: pieces_by_group[1], 2: pieces_by_group[2]}

                # `PORT-1` step 3b-iv: the port facet groups (`201` / `202`)
                # are the surfaces each gap piece shares with its conductor
                # piece -- exactly the two planar cuts where the gap box's
                # y-faces cross the arc, since the box overhangs the tube in x
                # and z (`gap_half_xz > minor_radius`) and the tube can only
                # leave it through those faces. That is the gap-conductor
                # interface a lumped-port voltage integrates over (step 3b-v).
                #
                # They are NOT emitted as gmsh physical groups: dim-2 groups on
                # facets interior to the partition hang `model_to_mesh` at
                # `-n 2` (known-issues 9). The identical facet set is rebuilt
                # from the distributed *cell* tags after `model_to_mesh`, via
                # `_interface_facet_tags`. What is computed here is the CAD
                # cross-check -- OCC's own area for the surfaces, printed so
                # the meshed area has an independent number to be scored
                # against. Derived from the fragment's own boundaries;
                # absolute tags from before the fragment call mean nothing
                # after it.
                cad_areas = {}
                for gap_group, wire_group, facet_group in ((101, 1, 201),
                                                           (102, 2, 202)):
                    gap_boundary = {
                        surf
                        for vol in pieces_by_group[gap_group]
                        for _, surf in gmsh.model.getBoundary(
                            [(3, vol)], oriented=False, recursive=False
                        )
                    }
                    conductor_boundary = {
                        surf
                        for vol in pieces_by_group[wire_group]
                        for _, surf in gmsh.model.getBoundary(
                            [(3, vol)], oriented=False, recursive=False
                        )
                    }
                    shared = sorted(gap_boundary & conductor_boundary)
                    if not shared:
                        raise RuntimeError(
                            "two_torus_domain: gap group "
                            f"{group_names[gap_group]} shares no surface with "
                            f"{group_names[wire_group]}; the gap box is not "
                            "crossing the arc ends"
                        )
                    cad_areas[facet_group] = (
                        len(shared),
                        sum(gmsh.model.occ.getMass(2, s) for s in shared),
                    )

                print(
                    "[two-torus-mesh] port interfaces (CAD) "
                    + " ".join(
                        f"{tag}: {n} surface(s) area={area:.6e}"
                        for tag, (n, area) in sorted(cad_areas.items())
                    ),
                    flush=True,
                )

            else:
                # Fragment renumbers volumes; identify them by mass and centroid
                # rather than by the tags it hands back (same discipline as
                # loop_over_half_space_domain). Each torus is orders of magnitude
                # smaller than the air region, and the two tori are told apart by
                # the sign of their centroid z.
                torus_mass = 2.0 * np.pi**2 * major_radius * minor_radius**2
                wire_1_volume = None
                wire_2_volume = None
                air_volume = None
                for dim, tag in gmsh.model.getEntities(dim=3):
                    mass = gmsh.model.occ.getMass(dim, tag)
                    _, _, zc = gmsh.model.occ.getCenterOfMass(dim, tag)
                    if mass > 10.0 * torus_mass:
                        air_volume = tag
                    elif zc < 0.0:
                        wire_1_volume = tag
                    else:
                        wire_2_volume = tag

                if wire_1_volume is None or wire_2_volume is None or air_volume is None:
                    raise RuntimeError(
                        "two_torus_domain: fragment did not produce the expected two "
                        f"tori plus air volume (got {gmsh.model.getEntities(dim=3)})"
                    )

                gmsh.model.addPhysicalGroup(3, [wire_1_volume], tag=1)
                gmsh.model.setPhysicalName(3, 1, "wire_1")

                gmsh.model.addPhysicalGroup(3, [wire_2_volume], tag=2)
                gmsh.model.setPhysicalName(3, 2, "wire_2")

                gmsh.model.addPhysicalGroup(3, [air_volume], tag=3)
                gmsh.model.setPhysicalName(3, 3, "domain")

                wire_volumes = {1: [wire_1_volume], 2: [wire_2_volume]}

            # A face is on the outer boundary only if it is *flat against* a
            # wall (both bounding-box extremes on it), not merely within one
            # mesh size of it: fragment introduces interior faces, and the old
            # `< resolution` test would have swept some of them into the BC.
            #
            # `GEO-10`: the tolerance may not be roundoff-tight. gmsh inflates
            # an OCC entity's bounding box by its geometric tolerance, measured
            # 2026-08-06 at exactly **1.000e-07** on all six walls of this box
            # (`20260806T050143Z_GEO-10-probe.log`) — so `tol = 1e-9` rejected
            # every wall, `boundary_surfaces` came out empty, and the group was
            # never declared at all (known-issues 10). 1e-6 clears that padding
            # by 10x while staying four orders below the nearest interior face,
            # whose residual in the same probe is 2.000e-02.
            tol = 1e-6
            boundary_surfaces = []
            for dim, surf in gmsh.model.getEntities(dim=2):
                x_min, y_min, z_min, x_max, y_max, z_max = gmsh.model.getBoundingBox(dim, surf)
                on_wall = (
                    abs(x_min + box_half_x) < tol and abs(x_max + box_half_x) < tol
                    or abs(x_min - box_half_x) < tol and abs(x_max - box_half_x) < tol
                    or abs(y_min + box_half_y) < tol and abs(y_max + box_half_y) < tol
                    or abs(y_min - box_half_y) < tol and abs(y_max - box_half_y) < tol
                    or abs(z_min + box_half_z) < tol and abs(z_max + box_half_z) < tol
                    or abs(z_min - box_half_z) < tol and abs(z_max - box_half_z) < tol
                )
                if on_wall:
                    boundary_surfaces.append(surf)

            if boundary_surfaces:
                gmsh.model.addPhysicalGroup(2, boundary_surfaces, tag=1)
                gmsh.model.setPhysicalName(2, 1, "outer_boundary")

            if wire_resolution is None:
                gmsh.model.mesh.setSize(gmsh.model.getEntities(0), resolution)
            else:
                # Graded sizing: fine on the tori, coarsening with distance so a
                # large air box does not blow up the cell count.
                h_wire = float(wire_resolution)
                h_far = float(resolution if far_resolution is None else far_resolution)
                if h_wire <= 0.0 or h_far <= 0.0:
                    raise ValueError("wire_resolution and far_resolution must be positive")

                # Refine on the conductors and, when gapped, on the gap boxes
                # too -- the gap is the smallest feature in the model. Pieces
                # share surfaces after fragment, so de-duplicate.
                refine_volumes = list(wire_volumes[1]) + list(wire_volumes[2])
                if port_gap:
                    refine_volumes += pieces_by_group[101] + pieces_by_group[102]
                wire_surfaces = sorted(
                    {
                        surf
                        for vol in refine_volumes
                        for _, surf in gmsh.model.getBoundary(
                            [(3, vol)], oriented=False, recursive=False
                        )
                    }
                )

                dist = gmsh.model.mesh.field.add("Distance")
                gmsh.model.mesh.field.setNumbers(dist, "SurfacesList", wire_surfaces)
                gmsh.model.mesh.field.setNumber(dist, "Sampling", 200)

                thr = gmsh.model.mesh.field.add("Threshold")
                gmsh.model.mesh.field.setNumber(thr, "InField", dist)
                gmsh.model.mesh.field.setNumber(thr, "SizeMin", h_wire)
                gmsh.model.mesh.field.setNumber(thr, "SizeMax", h_far)
                gmsh.model.mesh.field.setNumber(thr, "DistMin", minor_radius)
                gmsh.model.mesh.field.setNumber(thr, "DistMax", major_radius + padding)

                gmsh.model.mesh.field.setAsBackgroundMesh(thr)
                # Background field must win over point/curve-derived sizing.
                gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
                gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
                gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

            gmsh.model.mesh.generate(3)
            gmsh.model.mesh.optimize("Netgen")

        # `PORT-1` step 3b-iv: gmshio's default partitioner is
        # `GhostMode.none`, which leaves `cells_ghost = 0` on every rank. The
        # port facets rebuilt below are *interior* to the mesh, so classifying
        # one needs the tag of the cell on both sides — and on a partition
        # boundary one of those cells lives on the other rank. `shared_facet`
        # is what makes that cell present as a ghost; it is also what a `dS`
        # integral over those facets needs. Plumbed here only, so no other
        # fixture changes partition.
        partitioner = dolfinx.mesh.create_cell_partitioner(
            dolfinx.mesh.GhostMode.shared_facet
        )
        mesh, cell_tags, facet_tags = gmshio.model_to_mesh(
            gmsh.model, comm, rank, gdim=3, partitioner=partitioner
        )

        if comm.rank == rank:
            gmsh.finalize()

        if port_gap:
            # `PORT-1` step 3b-iv: rebuild the port facet groups from the
            # distributed cell tags (see the CAD-side comment above and
            # known-issues 9). gap_1 <-> wire_1 is port 201, gap_2 <-> wire_2
            # is port 202.
            facet_tags = _interface_facet_tags(
                mesh, cell_tags, {201: (101, 1), 202: (102, 2)}, facet_tags
            )

        return mesh, cell_tags, facet_tags

    @staticmethod
    def loop_over_half_space_domain(
        loop_radius: float = 0.04,
        wire_radius: float = 0.005,
        liftoff: float = 0.015,
        box_half_width: float = 0.10,
        resolution_wire: float = 0.004,
        resolution_near: float = 0.005,
        resolution_far: float = 0.02,
        near_half_width: float = 0.06,
        near_depth: float = 0.05,
        near_height: float = 0.025,
        comm: MPI.Intracomm = MPI.COMM_WORLD,
        rank: int = 0,
    ) -> Tuple[dolfinx.mesh.Mesh, dolfinx.mesh.MeshTags, dolfinx.mesh.MeshTags]:
        """Filamentary loop at height ``liftoff`` over a conductive half-space.

        `MAT-6` step 2: the FEM counterpart of
        :func:`~fem_em_solver.utils.dodd_deeds.coil_impedance_change`.  A torus
        of major radius ``loop_radius`` and minor radius ``wire_radius`` sits in
        the plane ``z = liftoff``; the cube ``[-W, W]³`` around it is split at
        ``z = 0`` into an upper air region and a lower slab that stands in for
        the half-space.  The slab fills the whole lower half of the box, so the
        PEC truncation plane below it sits many skin depths into the conductor
        and the half-space is only truncated where the fields are already dead.

        Cell tags: ``1`` wire, ``2`` air (``z > 0``), ``3`` slab (``z < 0``).
        Facet tag ``1`` is the outer boundary of the cube.

        Sizing is **graded**, deliberately: a single global ``setSize`` fine
        enough to put 3–4 cells across the skin depth would be unaffordable over
        the whole air box, and the tight-padding/uniform-size pattern is exactly
        what cost 20% on Helmholtz (docs/testing/known-issues.md).  Three scales:
        ``resolution_wire`` on the torus surface, ``resolution_near`` inside the
        near-field box ``|x|,|y| ≤ near_half_width``,
        ``−near_depth ≤ z ≤ near_height`` (which must contain the coil and the
        skin layer), and ``resolution_far`` everywhere else.

        Parameters
        ----------
        loop_radius, wire_radius, liftoff : float
            Loop major radius ``a``, wire minor radius, and the height ``h`` of
            the loop plane above the conductor surface [m].  The wire must clear
            the interface: ``liftoff > wire_radius``.
        box_half_width : float
            Half side ``W`` of the cubic truncation box [m].  This is the knob
            the `MAT-6` step-2a probe sweeps: ``ΔZ`` is extracted from a
            loaded/free *difference*, so the coil self-impedance cancels, but
            the PEC wall still images the induced currents.
        resolution_wire, resolution_near, resolution_far : float
            Target mesh sizes [m] for the three zones described above.
        near_half_width, near_depth, near_height : float
            Extent of the fine near-field box [m]: lateral half-width, depth
            below the interface, height above it.
        """
        if liftoff <= wire_radius:
            raise ValueError(
                f"liftoff={liftoff!r} must exceed wire_radius={wire_radius!r} so the "
                "wire clears the half-space interface"
            )
        if box_half_width <= loop_radius + wire_radius:
            raise ValueError(
                f"box_half_width={box_half_width!r} must exceed the loop outer radius "
                f"{loop_radius + wire_radius!r}"
            )
        for name, value in (
            ("resolution_wire", resolution_wire),
            ("resolution_near", resolution_near),
            ("resolution_far", resolution_far),
        ):
            if value <= 0.0:
                raise ValueError(f"{name} must be positive, got {value!r}")

        W = float(box_half_width)

        if comm.rank == rank:
            gmsh.initialize()
            gmsh.model.add("loop_over_half_space")

            wire = gmsh.model.occ.addTorus(0, 0, liftoff, loop_radius, wire_radius)
            air = gmsh.model.occ.addBox(-W, -W, 0.0, 2 * W, 2 * W, W)
            slab = gmsh.model.occ.addBox(-W, -W, -W, 2 * W, 2 * W, W)

            gmsh.model.occ.fragment([(3, air), (3, slab)], [(3, wire)])
            gmsh.model.occ.synchronize()

            # Identify the three volumes by mass and centroid rather than by the
            # tags fragment happens to hand back: the wire is orders of magnitude
            # the smallest, and air/slab are told apart by the sign of z̄.
            wire_volume = None
            air_volume = None
            slab_volume = None
            torus_mass = 2.0 * np.pi**2 * loop_radius * wire_radius**2
            for dim, tag in gmsh.model.getEntities(dim=3):
                mass = gmsh.model.occ.getMass(dim, tag)
                _, _, zc = gmsh.model.occ.getCenterOfMass(dim, tag)
                if mass < 10.0 * torus_mass:
                    wire_volume = tag
                elif zc > 0.0:
                    air_volume = tag
                else:
                    slab_volume = tag

            if wire_volume is None or air_volume is None or slab_volume is None:
                raise RuntimeError(
                    "loop_over_half_space_domain: fragment did not produce the expected "
                    f"wire/air/slab volumes (got {gmsh.model.getEntities(dim=3)})"
                )

            gmsh.model.addPhysicalGroup(3, [wire_volume], tag=1)
            gmsh.model.setPhysicalName(3, 1, "wire")
            gmsh.model.addPhysicalGroup(3, [air_volume], tag=2)
            gmsh.model.setPhysicalName(3, 2, "air")
            gmsh.model.addPhysicalGroup(3, [slab_volume], tag=3)
            gmsh.model.setPhysicalName(3, 3, "slab")

            # `GEO-12`: 1e-9 -> 1e-6, exactly `GEO-10`'s fix and for the same
            # measured reason. gmsh inflates an OCC entity's bounding box by its
            # geometric tolerance — 1.000e-07 here as on `two_torus_domain`
            # (`20260806T140325Z_GEO-11-probe.log`) — so `tol = 1e-9` sat 100x
            # *below* the padding, accepted 0 of 12 surfaces, and the group was
            # never declared (known-issues 12). The nearest interior face sits at
            # 9.000e-02, five orders above 1e-6, so the interior-face protection
            # the tight test existed for is intact.
            tol = 1e-6
            boundary_surfaces = []
            for dim, surf in gmsh.model.getEntities(dim=2):
                x0, y0, z0, x1, y1, z1 = gmsh.model.getBoundingBox(dim, surf)
                on_wall = (
                    abs(x0 + W) < tol and abs(x1 + W) < tol
                    or abs(x0 - W) < tol and abs(x1 - W) < tol
                    or abs(y0 + W) < tol and abs(y1 + W) < tol
                    or abs(y0 - W) < tol and abs(y1 - W) < tol
                    or abs(z0 + W) < tol and abs(z1 + W) < tol
                    or abs(z0 - W) < tol and abs(z1 - W) < tol
                )
                if on_wall:
                    boundary_surfaces.append(surf)
            if boundary_surfaces:
                gmsh.model.addPhysicalGroup(2, boundary_surfaces, tag=1)
                gmsh.model.setPhysicalName(2, 1, "outer_boundary")

            wire_surfaces = [
                surf
                for _, surf in gmsh.model.getBoundary(
                    [(3, wire_volume)], oriented=False, recursive=False
                )
            ]

            dist = gmsh.model.mesh.field.add("Distance")
            gmsh.model.mesh.field.setNumbers(dist, "SurfacesList", wire_surfaces)
            gmsh.model.mesh.field.setNumber(dist, "Sampling", 200)

            wire_thr = gmsh.model.mesh.field.add("Threshold")
            gmsh.model.mesh.field.setNumber(wire_thr, "InField", dist)
            gmsh.model.mesh.field.setNumber(wire_thr, "SizeMin", resolution_wire)
            gmsh.model.mesh.field.setNumber(wire_thr, "SizeMax", resolution_far)
            gmsh.model.mesh.field.setNumber(wire_thr, "DistMin", wire_radius)
            gmsh.model.mesh.field.setNumber(wire_thr, "DistMax", W)

            near = gmsh.model.mesh.field.add("Box")
            gmsh.model.mesh.field.setNumber(near, "VIn", resolution_near)
            gmsh.model.mesh.field.setNumber(near, "VOut", resolution_far)
            gmsh.model.mesh.field.setNumber(near, "XMin", -near_half_width)
            gmsh.model.mesh.field.setNumber(near, "XMax", near_half_width)
            gmsh.model.mesh.field.setNumber(near, "YMin", -near_half_width)
            gmsh.model.mesh.field.setNumber(near, "YMax", near_half_width)
            gmsh.model.mesh.field.setNumber(near, "ZMin", -near_depth)
            gmsh.model.mesh.field.setNumber(near, "ZMax", near_height)
            # Blend over one far-cell so the near/far jump is not a mesh shock.
            gmsh.model.mesh.field.setNumber(near, "Thickness", resolution_far)

            combined = gmsh.model.mesh.field.add("Min")
            gmsh.model.mesh.field.setNumbers(combined, "FieldsList", [wire_thr, near])
            gmsh.model.mesh.field.setAsBackgroundMesh(combined)

            gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
            gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
            gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

            gmsh.model.mesh.generate(3)

        mesh, cell_tags, facet_tags = gmshio.model_to_mesh(
            gmsh.model, comm, rank, gdim=3
        )

        if comm.rank == rank:
            gmsh.finalize()

        return mesh, cell_tags, facet_tags

    @staticmethod
    def sphere_in_box_domain(
        sphere_radius: float = 0.05,
        box_half_width: float = 0.10,
        resolution_sphere: float = 0.0125,
        resolution_far: float = 0.025,
        comm: MPI.Intracomm = MPI.COMM_WORLD,
        rank: int = 0,
    ) -> Tuple[dolfinx.mesh.Mesh, dolfinx.mesh.MeshTags, dolfinx.mesh.MeshTags]:
        """Dielectric sphere centred in a cubic air box (`TH-8`).

        Cell tags: ``1`` sphere, ``2`` air.  Facet tag ``1`` is the outer
        boundary of the cube.

        Sizing is graded through a ``Ball`` field rather than a single global
        ``setSize``: the interior of the sphere is where the gate measures, and
        an unsigned ``Distance`` field from the sphere *surface* would coarsen
        towards the centre, which is exactly the region that must stay
        resolved.  The far zone only has to carry a smooth exterior field, so
        ``resolution_far`` may be several times ``resolution_sphere`` (the
        tight-padding/uniform-size pattern that cost 20% on Helmholtz is
        avoided by keeping the box independent of the sphere resolution).

        Parameters
        ----------
        sphere_radius : float
            Sphere radius ``R`` [m].
        box_half_width : float
            Half side ``W`` of the cubic truncation box [m].  `TH-8` imposes the
            exact exterior (uniform + dipole) field on this wall, so ``W`` sets
            how much air is discretised, not how wrong the truncation is.
        resolution_sphere, resolution_far : float
            Target mesh sizes [m] inside ``1.2 R`` and in the remaining air.
        """
        R = float(sphere_radius)
        W = float(box_half_width)
        if R <= 0.0:
            raise ValueError(f"sphere_radius must be positive, got {sphere_radius!r}")
        if W <= R:
            raise ValueError(
                f"box_half_width={box_half_width!r} must exceed sphere_radius={sphere_radius!r}"
            )
        for name, value in (
            ("resolution_sphere", resolution_sphere),
            ("resolution_far", resolution_far),
        ):
            if value <= 0.0:
                raise ValueError(f"{name} must be positive, got {value!r}")

        if comm.rank == rank:
            gmsh.initialize()
            gmsh.model.add("sphere_in_box")

            sphere = gmsh.model.occ.addSphere(0.0, 0.0, 0.0, R)
            box = gmsh.model.occ.addBox(-W, -W, -W, 2 * W, 2 * W, 2 * W)

            gmsh.model.occ.fragment([(3, box)], [(3, sphere)])
            gmsh.model.occ.synchronize()

            # Identify by mass, not by the tags fragment hands back.
            sphere_mass = 4.0 / 3.0 * np.pi * R**3
            sphere_volume = None
            air_volume = None
            for dim, tag in gmsh.model.getEntities(dim=3):
                mass = gmsh.model.occ.getMass(dim, tag)
                if abs(mass - sphere_mass) < 0.05 * sphere_mass:
                    sphere_volume = tag
                else:
                    air_volume = tag

            if sphere_volume is None or air_volume is None:
                raise RuntimeError(
                    "sphere_in_box_domain: fragment did not produce the expected "
                    f"sphere/air volumes (got {gmsh.model.getEntities(dim=3)})"
                )

            gmsh.model.addPhysicalGroup(3, [sphere_volume], tag=1)
            gmsh.model.setPhysicalName(3, 1, "sphere")
            gmsh.model.addPhysicalGroup(3, [air_volume], tag=2)
            gmsh.model.setPhysicalName(3, 2, "air")

            # `GEO-12`: 1e-9 -> 1e-6, same measured defect as above and as
            # `GEO-10`. The OCC bounding-box padding is 1.000e-07, so the old
            # tolerance accepted 0 of 7 surfaces and never declared the group
            # (known-issues 12); the nearest interior face is at 1.500e-01.
            tol = 1e-6
            boundary_surfaces = []
            for dim, surf in gmsh.model.getEntities(dim=2):
                x0, y0, z0, x1, y1, z1 = gmsh.model.getBoundingBox(dim, surf)
                on_wall = (
                    abs(x0 + W) < tol and abs(x1 + W) < tol
                    or abs(x0 - W) < tol and abs(x1 - W) < tol
                    or abs(y0 + W) < tol and abs(y1 + W) < tol
                    or abs(y0 - W) < tol and abs(y1 - W) < tol
                    or abs(z0 + W) < tol and abs(z1 + W) < tol
                    or abs(z0 - W) < tol and abs(z1 - W) < tol
                )
                if on_wall:
                    boundary_surfaces.append(surf)
            if boundary_surfaces:
                gmsh.model.addPhysicalGroup(2, boundary_surfaces, tag=1)
                gmsh.model.setPhysicalName(2, 1, "outer_boundary")

            ball = gmsh.model.mesh.field.add("Ball")
            gmsh.model.mesh.field.setNumber(ball, "XCenter", 0.0)
            gmsh.model.mesh.field.setNumber(ball, "YCenter", 0.0)
            gmsh.model.mesh.field.setNumber(ball, "ZCenter", 0.0)
            gmsh.model.mesh.field.setNumber(ball, "Radius", 1.2 * R)
            gmsh.model.mesh.field.setNumber(ball, "VIn", resolution_sphere)
            gmsh.model.mesh.field.setNumber(ball, "VOut", resolution_far)
            # Blend over one far-cell so the near/far jump is not a mesh shock.
            gmsh.model.mesh.field.setNumber(ball, "Thickness", resolution_far)
            gmsh.model.mesh.field.setAsBackgroundMesh(ball)

            gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
            gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
            gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

            gmsh.model.mesh.generate(3)

        mesh, cell_tags, facet_tags = gmshio.model_to_mesh(
            gmsh.model, comm, rank, gdim=3
        )

        if comm.rank == rank:
            gmsh.finalize()

        return mesh, cell_tags, facet_tags

    @staticmethod
    def coil_phantom_domain_sizing_diagnostics(
        *,
        coil_major_radius: float,
        coil_minor_radius: float,
        coil_separation: float,
        phantom_radius: float,
        phantom_height: float,
        air_padding: float,
        phantom_offset_xy: Tuple[float, float] = (0.0, 0.0),
        min_air_padding_ratio: float = 0.35,
    ) -> Dict[str, float | bool]:
        """Compute air-box sizing diagnostics for the coil+phantom fixture.

        The returned values are lightweight geometry heuristics (no meshing).
        They are used to flag undersized domains that can amplify boundary artifacts.

        Sizing rule (the intent the numbers encode, `GEO-4` step 1): the air box is
        **centred on the origin** (see `coil_phantom_domain`, which builds it from
        these extents), so its half-width must contain every object's largest |x|:

            half_width = max(coil_major + coil_minor, |offset| + phantom_radius)
                         + padding

        An off-centre phantom therefore enters through the second term of the max
        and only *governs* the box once it reaches outside the coil envelope. Below
        that it is masked by the coil, and the correct domain does not grow — the
        clearance to the wall shrinks instead, which is what
        `phantom_boundary_clearance_m` reports.
        """
        if min_air_padding_ratio <= 0.0:
            raise ValueError("min_air_padding_ratio must be > 0")
        if air_padding < 0.0:
            raise ValueError("air_padding must be >= 0")

        phantom_cx, phantom_cy = float(phantom_offset_xy[0]), float(phantom_offset_xy[1])
        phantom_offset_radius = np.sqrt(phantom_cx**2 + phantom_cy**2)

        radial_extent_without_padding = max(
            coil_major_radius + coil_minor_radius,
            phantom_offset_radius + phantom_radius,
        )
        z_offset = coil_separation / 2.0
        z_extent_without_padding = max(z_offset + coil_minor_radius, phantom_height / 2.0)

        reference_extent = max(radial_extent_without_padding, z_extent_without_padding)
        recommended_min_padding = min_air_padding_ratio * reference_extent
        effective_air_padding = max(air_padding, recommended_min_padding)

        # Clearance from the phantom's outermost radial point to the recommended
        # wall. By construction of the max above this is >= recommended_min_padding,
        # with equality exactly when the phantom governs the box.
        phantom_outer_radial_extent = phantom_offset_radius + phantom_radius
        recommended_domain_half_width = radial_extent_without_padding + recommended_min_padding
        phantom_boundary_clearance = recommended_domain_half_width - phantom_outer_radial_extent

        return {
            "phantom_offset_radius_m": float(phantom_offset_radius),
            "phantom_outer_radial_extent_m": float(phantom_outer_radial_extent),
            "phantom_boundary_clearance_m": float(phantom_boundary_clearance),
            "phantom_governs_radial_extent": bool(
                phantom_outer_radial_extent >= coil_major_radius + coil_minor_radius
            ),
            "radial_extent_without_padding_m": float(radial_extent_without_padding),
            "z_extent_without_padding_m": float(z_extent_without_padding),
            "reference_extent_m": float(reference_extent),
            "provided_air_padding_m": float(air_padding),
            "recommended_min_air_padding_m": float(recommended_min_padding),
            "effective_air_padding_m": float(effective_air_padding),
            "is_domain_undersized": bool(air_padding < recommended_min_padding),
            "recommended_domain_half_width_m": float(recommended_domain_half_width),
            "recommended_domain_half_height_m": float(z_extent_without_padding + recommended_min_padding),
        }

    @staticmethod
    def coil_phantom_geometry_sanity_report(
        *,
        cell_tags: dolfinx.mesh.MeshTags,
        coil_major_radius: float,
        coil_minor_radius: float,
        coil_separation: float,
        phantom_radius: float,
        phantom_height: float,
        air_padding: float,
        phantom_offset_xy: Tuple[float, float] = (0.0, 0.0),
        comm: MPI.Intracomm = MPI.COMM_WORLD,
    ) -> Dict[str, object]:
        """Build a compact geometry/tag sanity report for the coil+phantom fixture.

        The report combines:
        - required tag counts (global)
        - expected analytic region-volume ratios (coil/phantom/air)
        - observed tag cell-count ratios
        - lightweight warnings for obviously suspicious setups
        """
        required_tags = {
            1: "coil_1",
            2: "coil_2",
            3: "phantom",
            4: "air",
        }

        counts = {}
        for tag in required_tags:
            local = int(np.count_nonzero(cell_tags.values == tag))
            counts[tag] = int(comm.allreduce(local, op=MPI.SUM))

        total_cells = int(sum(counts.values()))
        observed_cell_ratios = {
            tag: (counts[tag] / total_cells if total_cells > 0 else 0.0)
            for tag in required_tags
        }

        sizing = MeshGenerator.coil_phantom_domain_sizing_diagnostics(
            coil_major_radius=coil_major_radius,
            coil_minor_radius=coil_minor_radius,
            coil_separation=coil_separation,
            phantom_radius=phantom_radius,
            phantom_height=phantom_height,
            air_padding=air_padding,
            phantom_offset_xy=phantom_offset_xy,
        )

        effective_air_padding = sizing["effective_air_padding_m"]
        radial_extent = sizing["radial_extent_without_padding_m"]
        z_extent = sizing["z_extent_without_padding_m"]

        box_volume = (
            (2.0 * (radial_extent + effective_air_padding))
            * (2.0 * (radial_extent + effective_air_padding))
            * (2.0 * (z_extent + effective_air_padding))
        )
        coil_single_volume = 2.0 * np.pi**2 * coil_major_radius * (coil_minor_radius**2)
        phantom_volume = np.pi * (phantom_radius**2) * phantom_height
        occupied_volume = 2.0 * coil_single_volume + phantom_volume
        air_volume = max(0.0, box_volume - occupied_volume)

        expected_volumes = {
            1: float(coil_single_volume),
            2: float(coil_single_volume),
            3: float(phantom_volume),
            4: float(air_volume),
        }
        expected_total_volume = float(sum(expected_volumes.values()))
        expected_volume_ratios = {
            tag: (expected_volumes[tag] / expected_total_volume if expected_total_volume > 0.0 else 0.0)
            for tag in required_tags
        }

        warnings: List[str] = []
        missing = [required_tags[tag] for tag, count in counts.items() if count <= 0]
        if missing:
            warnings.append(f"missing required tags: {', '.join(missing)}")

        if sizing["is_domain_undersized"]:
            warnings.append(
                "air padding below recommended minimum "
                f"({sizing['provided_air_padding_m']:.6e} < {sizing['recommended_min_air_padding_m']:.6e} m)"
            )

        for tag, name in required_tags.items():
            expected_ratio = expected_volume_ratios[tag]
            observed_ratio = observed_cell_ratios[tag]
            if expected_ratio > 0.0 and observed_ratio > 0.0:
                mismatch = max(observed_ratio / expected_ratio, expected_ratio / observed_ratio)
                if mismatch > 5.0:
                    warnings.append(
                        f"{name} observed/expected ratio mismatch is large "
                        f"(observed={observed_ratio:.3f}, expected={expected_ratio:.3f})"
                    )

        return {
            "required_tag_counts": {
                required_tags[tag]: counts[tag] for tag in required_tags
            },
            "expected_volume_ratios": {
                required_tags[tag]: expected_volume_ratios[tag] for tag in required_tags
            },
            "observed_cell_ratios": {
                required_tags[tag]: observed_cell_ratios[tag] for tag in required_tags
            },
            "effective_air_padding_m": float(effective_air_padding),
            "warnings": warnings,
            "ok": len(warnings) == 0,
        }

    @staticmethod
    def print_coil_phantom_geometry_sanity_report(
        *,
        report: Dict[str, object],
        prefix: str = "[coil-phantom-sanity] ",
        comm: MPI.Intracomm = MPI.COMM_WORLD,
    ) -> None:
        """Print a deterministic, compact sanity report on rank 0."""
        if comm.rank != 0:
            return

        print(f"{prefix}geometry sanity report:")

        counts = report["required_tag_counts"]
        print(f"{prefix}required tag counts:")
        for name in ("coil_1", "coil_2", "phantom", "air"):
            print(f"{prefix}  {name}: {counts[name]}")

        expected = report["expected_volume_ratios"]
        observed = report["observed_cell_ratios"]
        print(f"{prefix}volume ratio check (expected_volume_ratio vs observed_cell_ratio):")
        for name in ("coil_1", "coil_2", "phantom", "air"):
            print(f"{prefix}  {name}: expected={expected[name]:.6f}, observed={observed[name]:.6f}")

        print(f"{prefix}effective air padding: {report['effective_air_padding_m']:.6e} m")

        warnings = report["warnings"]
        if warnings:
            print(f"{prefix}warnings:")
            for warning in warnings:
                print(f"{prefix}  - {warning}")
        else:
            print(f"{prefix}warnings: none")

    @staticmethod
    def coil_phantom_region_resolution_policy(
        *,
        resolution: float,
        coil_resolution: Optional[float] = None,
        phantom_resolution: Optional[float] = None,
        air_resolution: Optional[float] = None,
        region_resolutions: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Resolve per-region mesh resolution policy for coil+phantom fixtures.

        Resolution precedence (highest to lowest):
        1) Explicit keyword args (``coil_resolution``, ``phantom_resolution``, ``air_resolution``)
        2) ``region_resolutions`` mapping keys: ``coil``, ``phantom``, ``air``
        3) Global ``resolution`` fallback
        """
        if resolution <= 0.0:
            raise ValueError("resolution must be > 0")

        mapping = region_resolutions or {}
        allowed_mapping_keys = {"coil", "phantom", "air"}
        unknown_keys = sorted(set(mapping.keys()) - allowed_mapping_keys)
        if unknown_keys:
            raise ValueError(
                "region_resolutions contains unsupported keys: "
                f"{unknown_keys}; allowed keys are {sorted(allowed_mapping_keys)}"
            )

        coil_h = float(coil_resolution if coil_resolution is not None else mapping.get("coil", resolution))
        phantom_h = float(
            phantom_resolution if phantom_resolution is not None else mapping.get("phantom", resolution)
        )
        air_h = float(air_resolution if air_resolution is not None else mapping.get("air", resolution))

        for name, h in (("coil", coil_h), ("phantom", phantom_h), ("air", air_h)):
            if h <= 0.0:
                raise ValueError(f"{name}_resolution must be > 0 (got {h:.6e})")

        return {
            "coil_resolution_m": coil_h,
            "phantom_resolution_m": phantom_h,
            "air_resolution_m": air_h,
            "min_resolution_m": min(coil_h, phantom_h, air_h),
            "max_resolution_m": max(coil_h, phantom_h, air_h),
        }

    @staticmethod
    def coil_phantom_domain(
        coil_major_radius: float = 0.08,
        coil_minor_radius: float = 0.01,
        coil_separation: float = 0.08,
        phantom_radius: float = 0.04,
        phantom_height: float = 0.10,
        air_padding: float = 0.04,
        resolution: float = 0.015,
        coil_resolution: Optional[float] = None,
        phantom_resolution: Optional[float] = None,
        air_resolution: Optional[float] = None,
        region_resolutions: Optional[Dict[str, float]] = None,
        phantom_placement_preset: str = "centered",
        phantom_offset_xy: Optional[Tuple[float, float]] = None,
        comm: MPI.Intracomm = MPI.COMM_WORLD,
        rank: int = 0,
    ) -> Tuple[dolfinx.mesh.Mesh, dolfinx.mesh.MeshTags, dolfinx.mesh.MeshTags]:
        """Generate a coarse two-coil + cylindrical phantom + air mesh.

        Parameters
        ----------
        coil_resolution, phantom_resolution, air_resolution : float | None
            Optional per-region characteristic mesh sizes [m].
            When omitted, ``resolution`` is used. Smaller values refine locally.
        region_resolutions : dict[str, float] | None
            Optional mapping with keys ``coil``, ``phantom``, ``air`` as an
            alternative to individual keyword arguments.
        phantom_placement_preset : str
            Placement preset for phantom center in the xy-plane.
            Supported values: ``centered`` and ``off_center``.
        phantom_offset_xy : tuple[float, float] | None
            Optional explicit ``(x, y)`` phantom center offset [m]. When provided,
            this overrides the preset offset.

        Cell tags:
        - 1: coil_1
        - 2: coil_2
        - 3: phantom
        - 4: air
        """
        allowed_presets = {"centered", "off_center"}
        if phantom_placement_preset not in allowed_presets:
            raise ValueError(
                "phantom_placement_preset must be one of "
                f"{sorted(allowed_presets)}, got '{phantom_placement_preset}'"
            )

        if phantom_offset_xy is None:
            if phantom_placement_preset == "centered":
                phantom_cx, phantom_cy = 0.0, 0.0
            else:
                phantom_cx, phantom_cy = 0.35 * phantom_radius, 0.0
        else:
            phantom_cx, phantom_cy = float(phantom_offset_xy[0]), float(phantom_offset_xy[1])

        phantom_offset_radius = np.sqrt(phantom_cx**2 + phantom_cy**2)
        coil_inner_radius = coil_major_radius - coil_minor_radius
        radial_clearance = coil_inner_radius - (phantom_offset_radius + phantom_radius)
        if radial_clearance <= 0.0:
            raise ValueError(
                "Phantom overlaps coil conductor envelope for selected placement: "
                f"offset_radius={phantom_offset_radius:.6e} m, "
                f"phantom_radius={phantom_radius:.6e} m, "
                f"available_inner_radius={coil_inner_radius:.6e} m"
            )

        sizing = MeshGenerator.coil_phantom_domain_sizing_diagnostics(
            coil_major_radius=coil_major_radius,
            coil_minor_radius=coil_minor_radius,
            coil_separation=coil_separation,
            phantom_radius=phantom_radius,
            phantom_height=phantom_height,
            air_padding=air_padding,
            phantom_offset_xy=(phantom_cx, phantom_cy),
        )
        effective_air_padding = sizing["effective_air_padding_m"]

        if comm.rank == rank and sizing["is_domain_undersized"]:
            print(
                "[coil-phantom-domain] WARNING: requested air_padding is below recommended minimum; "
                f"provided={sizing['provided_air_padding_m']:.6e} m, "
                f"recommended_min={sizing['recommended_min_air_padding_m']:.6e} m. "
                f"Using effective air_padding={effective_air_padding:.6e} m to reduce boundary artifacts."
            )

        region_h = MeshGenerator.coil_phantom_region_resolution_policy(
            resolution=resolution,
            coil_resolution=coil_resolution,
            phantom_resolution=phantom_resolution,
            air_resolution=air_resolution,
            region_resolutions=region_resolutions,
        )

        if comm.rank == rank:
            gmsh.initialize()
            gmsh.model.add("coil_phantom_domain")

            z_offset = coil_separation / 2
            coil_1 = gmsh.model.occ.addTorus(0, 0, -z_offset, coil_major_radius, coil_minor_radius)
            coil_2 = gmsh.model.occ.addTorus(0, 0, z_offset, coil_major_radius, coil_minor_radius)
            phantom = gmsh.model.occ.addCylinder(
                phantom_cx,
                phantom_cy,
                -phantom_height / 2,
                0,
                0,
                phantom_height,
                phantom_radius,
            )

            radial_extent = sizing["radial_extent_without_padding_m"]
            z_extent = sizing["z_extent_without_padding_m"]
            air = gmsh.model.occ.addBox(
                -(radial_extent + effective_air_padding),
                -(radial_extent + effective_air_padding),
                -(z_extent + effective_air_padding),
                2 * (radial_extent + effective_air_padding),
                2 * (radial_extent + effective_air_padding),
                2 * (z_extent + effective_air_padding),
            )

            gmsh.model.occ.fragment(
                [(3, air)],
                [(3, coil_1), (3, coil_2), (3, phantom)],
            )
            gmsh.model.occ.synchronize()

            volumes = gmsh.model.getEntities(dim=3)
            masses = {tag: gmsh.model.occ.getMass(3, tag) for _, tag in volumes}

            # GEO-9 step 1: the group re-derivation below assumes fragment
            # returned exactly four volumes (air + two coils + phantom). An
            # extra piece (an overlap split off) would silently receive no
            # physical group and surface far downstream as a dolfinx gmshio
            # `assert len(entity_types) == 1`; a merged pair would raise
            # IndexError on the phantom_tag line. Fail here instead, with the
            # count and the masses that identify which happened.
            if len(volumes) != 4:
                raise RuntimeError(
                    "coil_phantom_domain: occ.fragment returned "
                    f"{len(volumes)} volumes, expected exactly 4 "
                    "(air + coil_1 + coil_2 + phantom); per-volume masses [m^3]: "
                    + ", ".join(f"tag {tag}: {mass:.6e}" for tag, mass in sorted(masses.items()))
                )

            air_tag = max(masses, key=masses.get)

            remaining = [tag for _, tag in volumes if tag != air_tag]
            z_centers = {
                tag: gmsh.model.occ.getCenterOfMass(3, tag)[2]
                for tag in remaining
            }

            coil_1_tag = min(remaining, key=lambda tag: z_centers[tag])
            coil_2_tag = max(remaining, key=lambda tag: z_centers[tag])
            phantom_tag = [tag for tag in remaining if tag not in (coil_1_tag, coil_2_tag)][0]

            gmsh.model.addPhysicalGroup(3, [coil_1_tag], tag=1)
            gmsh.model.setPhysicalName(3, 1, "coil_1")
            gmsh.model.addPhysicalGroup(3, [coil_2_tag], tag=2)
            gmsh.model.setPhysicalName(3, 2, "coil_2")
            gmsh.model.addPhysicalGroup(3, [phantom_tag], tag=3)
            gmsh.model.setPhysicalName(3, 3, "phantom")
            gmsh.model.addPhysicalGroup(3, [air_tag], tag=4)
            gmsh.model.setPhysicalName(3, 4, "air")

            # Every 3-D entity must carry a marker; a cell with none is exactly
            # what gmshio asserts on. Checked against the model, not against the
            # four tags we just wrote, so a renumbering by fragment cannot hide.
            grouped_volumes = set()
            for _, group_tag in gmsh.model.getPhysicalGroups(dim=3):
                grouped_volumes.update(gmsh.model.getEntitiesForPhysicalGroup(3, group_tag))
            ungrouped = sorted({tag for _, tag in volumes} - grouped_volumes)
            if ungrouped:
                raise RuntimeError(
                    "coil_phantom_domain: 3-D entities carry no physical group: "
                    f"{ungrouped}; masses [m^3]: "
                    + ", ".join(f"tag {tag}: {masses[tag]:.6e}" for tag in ungrouped)
                )

            print(
                f"[coil-phantom-mesh] fragment volumes={len(volumes)} masses[m^3]: "
                + ", ".join(f"{tag}:{mass:.6e}" for tag, mass in sorted(masses.items()))
                + f" | air={air_tag} coil_1={coil_1_tag} coil_2={coil_2_tag} phantom={phantom_tag}",
                flush=True,
            )

            outer_boundary_surfaces = []
            box_half_x = radial_extent + effective_air_padding
            box_half_z = z_extent + effective_air_padding
            for dim, surf in gmsh.model.getEntities(dim=2):
                x_min, y_min, z_min, x_max, y_max, z_max = gmsh.model.getBoundingBox(dim, surf)
                if (
                    abs(abs(x_min) - box_half_x) < resolution or abs(abs(x_max) - box_half_x) < resolution
                    or abs(abs(y_min) - box_half_x) < resolution or abs(abs(y_max) - box_half_x) < resolution
                    or abs(abs(z_min) - box_half_z) < resolution or abs(abs(z_max) - box_half_z) < resolution
                ):
                    outer_boundary_surfaces.append(surf)

            if outer_boundary_surfaces:
                gmsh.model.addPhysicalGroup(2, outer_boundary_surfaces, tag=1)
                gmsh.model.setPhysicalName(2, 1, "outer_boundary")

            def _collect_volume_point_tags(volume_tag: int) -> set[int]:
                surfaces = gmsh.model.getBoundary([(3, volume_tag)], oriented=False, recursive=False)
                curves = gmsh.model.getBoundary(surfaces, oriented=False, recursive=False)
                points = gmsh.model.getBoundary(curves, oriented=False, recursive=False)
                return {entity_tag for dim, entity_tag in points if dim == 0}

            point_size_targets: Dict[int, float] = {}

            def _assign_size(points: set[int], size_value: float) -> None:
                for point_tag in points:
                    if point_tag in point_size_targets:
                        point_size_targets[point_tag] = min(point_size_targets[point_tag], size_value)
                    else:
                        point_size_targets[point_tag] = size_value

            _assign_size(_collect_volume_point_tags(air_tag), region_h["air_resolution_m"])
            _assign_size(_collect_volume_point_tags(coil_1_tag), region_h["coil_resolution_m"])
            _assign_size(_collect_volume_point_tags(coil_2_tag), region_h["coil_resolution_m"])
            _assign_size(_collect_volume_point_tags(phantom_tag), region_h["phantom_resolution_m"])

            for point_tag, size_value in point_size_targets.items():
                gmsh.model.mesh.setSize([(0, point_tag)], size_value)

            gmsh.option.setNumber("Mesh.CharacteristicLengthMin", region_h["min_resolution_m"])
            gmsh.option.setNumber("Mesh.CharacteristicLengthMax", region_h["max_resolution_m"])

            print(
                "[coil-phantom-mesh] region resolution policy: "
                f"coil={region_h['coil_resolution_m']:.6e} m, "
                f"phantom={region_h['phantom_resolution_m']:.6e} m, "
                f"air={region_h['air_resolution_m']:.6e} m"
            )

            gmsh.model.mesh.generate(3)
            gmsh.model.mesh.optimize("Netgen")

        mesh, cell_tags, facet_tags = gmshio.model_to_mesh(
            gmsh.model, comm, rank, gdim=3
        )

        sanity_report = MeshGenerator.coil_phantom_geometry_sanity_report(
            cell_tags=cell_tags,
            coil_major_radius=coil_major_radius,
            coil_minor_radius=coil_minor_radius,
            coil_separation=coil_separation,
            phantom_radius=phantom_radius,
            phantom_height=phantom_height,
            air_padding=air_padding,
            phantom_offset_xy=(phantom_cx, phantom_cy),
            comm=comm,
        )
        MeshGenerator.print_coil_phantom_geometry_sanity_report(report=sanity_report, comm=comm)

        if comm.rank == rank:
            gmsh.finalize()

        return mesh, cell_tags, facet_tags

    @staticmethod
    def birdcage_port_layout_diagnostics(
        *,
        leg_count: int,
        ring_radius: float,
        leg_width: float,
        ring_minor_radius: float,
        phantom_radius: float,
        port_box_size: Tuple[float, float, float],
        port_clearance: float = 1.0e-3,
        min_port_face_area: float = 2.5e-5,
        min_port_center_separation: Optional[float] = None,
    ) -> Dict[str, float]:
        """Compute and validate birdcage port geometry diagnostics.

        This helper is intentionally lightweight and does not require meshing.
        It enforces a minimum port face area, checks center-to-center
        separation, and guards against radial overlap with conductor/phantom
        bulk regions.
        """
        if leg_count < 3:
            raise ValueError("leg_count must be >= 3 for port layout checks")
        if leg_width <= 0.0:
            raise ValueError("leg_width must be > 0")
        if ring_radius <= 0.0:
            raise ValueError("ring_radius must be > 0")

        port_dx, port_dy, port_dz = port_box_size
        if port_dx <= 0.0 or port_dy <= 0.0 or port_dz <= 0.0:
            raise ValueError("port_box_size components must be > 0")
        if ring_minor_radius <= 0.0:
            raise ValueError("ring_minor_radius must be > 0")
        if phantom_radius <= 0.0:
            raise ValueError("phantom_radius must be > 0")
        if port_clearance < 0.0:
            raise ValueError("port_clearance must be >= 0")

        port_face_area = port_dx * port_dz
        if port_face_area < min_port_face_area:
            raise ValueError(
                "Port face area too small for robust tagging: "
                f"area={port_face_area:.6e} m^2, required>={min_port_face_area:.6e} m^2"
            )

        leg_radius_eff = 0.5 * leg_width
        conductor_outer_radius = ring_radius + max(leg_radius_eff, ring_minor_radius)
        port_radius = conductor_outer_radius + 0.5 * port_dy + port_clearance

        theta = np.linspace(0.0, 2.0 * np.pi, leg_count, endpoint=False)
        port_centers = []
        for idx, angle in enumerate(theta):
            next_angle = theta[(idx + 1) % leg_count]
            midpoint_angle = np.arctan2(
                np.sin(angle) + np.sin(next_angle),
                np.cos(angle) + np.cos(next_angle),
            )
            port_centers.append(
                np.array([
                    port_radius * np.cos(midpoint_angle),
                    port_radius * np.sin(midpoint_angle),
                ])
            )

        min_center_separation = float("inf")
        for idx in range(len(port_centers)):
            for jdx in range(idx + 1, len(port_centers)):
                distance = float(np.linalg.norm(port_centers[idx] - port_centers[jdx]))
                min_center_separation = min(min_center_separation, distance)

        if min_port_center_separation is None:
            min_port_center_separation = max(5.0e-4, 1.25 * max(port_dx, port_dy))

        if min_center_separation < min_port_center_separation:
            raise ValueError(
                "Port center separation too small: "
                f"min={min_center_separation:.6e} m, "
                f"required>={min_port_center_separation:.6e} m"
            )

        conductor_radial_clearance = port_radius - 0.5 * port_dy - conductor_outer_radius
        phantom_radial_clearance = port_radius - 0.5 * port_dy - phantom_radius

        if conductor_radial_clearance <= 0.0:
            raise ValueError(
                "Port/conductor radial overlap detected: "
                f"clearance={conductor_radial_clearance:.6e} m"
            )
        if phantom_radial_clearance <= 0.0:
            raise ValueError(
                "Port/phantom radial overlap detected: "
                f"clearance={phantom_radial_clearance:.6e} m"
            )

        return {
            "port_face_area_m2": float(port_face_area),
            "min_port_face_area_m2": float(min_port_face_area),
            "min_port_center_separation_m": float(min_center_separation),
            "required_port_center_separation_m": float(min_port_center_separation),
            "conductor_radial_clearance_m": float(conductor_radial_clearance),
            "phantom_radial_clearance_m": float(phantom_radial_clearance),
            "port_radius_m": float(port_radius),
            "conductor_outer_radius_m": float(conductor_outer_radius),
        }

    @staticmethod
    def birdcage_port_domain(
        leg_count: int = 4,
        ring_radius: float = 0.07,
        leg_width: float = 0.012,
        leg_spacing: float = 0.11,
        coil_length: float = 0.14,
        ring_minor_radius: float = 0.004,
        phantom_radius: float = 0.03,
        phantom_height: float = 0.08,
        port_box_size: Tuple[float, float, float] = (0.010, 0.008, 0.010),
        port_clearance: float = 1.0e-3,
        min_port_face_area: float = 2.5e-5,
        min_port_center_separation: Optional[float] = None,
        air_padding: float = 0.03,
        resolution: float = 0.015,
        comm: MPI.Intracomm = MPI.COMM_WORLD,
        rank: int = 0,
        n_legs: Optional[int] = None,
        leg_radius: Optional[float] = None,
        leg_height: Optional[float] = None,
    ) -> Tuple[dolfinx.mesh.Mesh, dolfinx.mesh.MeshTags, dolfinx.mesh.MeshTags]:
        """Generate a coarse, parametric birdcage-like geometry fixture with port tags.

        Parameters
        ----------
        leg_count : int
            Number of birdcage legs distributed uniformly around the ring.
        ring_radius : float
            Radius of the birdcage rings [m].
        leg_width : float
            Leg diameter [m].
        leg_spacing : float
            Center-to-center spacing between bottom and top ring planes [m].
        coil_length : float
            Axial conductor span used for vertical legs [m].

        Notes
        -----
        `n_legs`, `leg_radius`, and `leg_height` are accepted as backward-compatible
        aliases and map to `leg_count`, `leg_width/2`, and `coil_length` respectively.

        Cell tags:
        - 1: conductor (rings + legs)
        - 2: air
        - 3: phantom
        - 101..(100+leg_count): per-port regions between adjacent legs
        """
        if n_legs is not None:
            leg_count = n_legs
        if leg_radius is not None:
            leg_width = 2.0 * leg_radius
        if leg_height is not None:
            coil_length = leg_height

        if leg_count < 3:
            raise ValueError("leg_count must be >= 3 for a birdcage-like fixture")
        if leg_width <= 0.0:
            raise ValueError("leg_width must be > 0")
        if leg_spacing <= 0.0:
            raise ValueError("leg_spacing must be > 0")
        if coil_length <= 0.0:
            raise ValueError("coil_length must be > 0")
        if ring_radius <= 0.0:
            raise ValueError("ring_radius must be > 0")

        leg_radius_eff = 0.5 * leg_width
        port_diagnostics = MeshGenerator.birdcage_port_layout_diagnostics(
            leg_count=leg_count,
            ring_radius=ring_radius,
            leg_width=leg_width,
            ring_minor_radius=ring_minor_radius,
            phantom_radius=phantom_radius,
            port_box_size=port_box_size,
            port_clearance=port_clearance,
            min_port_face_area=min_port_face_area,
            min_port_center_separation=min_port_center_separation,
        )

        # The generator below can raise (overlapping facets, GEO-9 step 2b). Two
        # things must happen when it does, or the failure poisons the rest of the
        # process: gmsh must be finalized (otherwise it stays initialised and
        # mid-command, and every later `occ` call in this process is refused —
        # that is known-issues 7), and the *other* ranks must be told, or they
        # block forever in the collective `model_to_mesh` below that the raising
        # rank never reaches. Both were measured: 20260803T123116Z log, 5 failed
        # 2 passed in 3.16 s of pytest but harness exit 124 at the 180 s ceiling.
        build_error: Optional[BaseException] = None
        if comm.rank == rank:
            try:
                MeshGenerator._build_birdcage_port_model(
                    leg_count=leg_count,
                    ring_radius=ring_radius,
                    leg_radius_eff=leg_radius_eff,
                    leg_spacing=leg_spacing,
                    coil_length=coil_length,
                    ring_minor_radius=ring_minor_radius,
                    phantom_radius=phantom_radius,
                    phantom_height=phantom_height,
                    port_box_size=port_box_size,
                    port_radius=port_diagnostics["port_radius_m"],
                    air_padding=air_padding,
                    resolution=resolution,
                )
            except BaseException as exc:  # noqa: BLE001 — re-raised below, on every rank
                build_error = exc
                if gmsh.isInitialized():
                    gmsh.finalize()

        # Collective: every rank learns whether the geometry exists before any of
        # them enters `model_to_mesh`.
        if comm.bcast(build_error is not None, root=rank):
            if build_error is not None:
                raise build_error
            raise RuntimeError(
                f"birdcage_port_domain geometry generation failed on rank {rank}"
            )

        mesh, cell_tags, facet_tags = gmshio.model_to_mesh(
            gmsh.model, comm, rank, gdim=3
        )

        if comm.rank == rank:
            gmsh.finalize()

        return mesh, cell_tags, facet_tags

    @staticmethod
    def _build_birdcage_port_model(
        *,
        leg_count: int,
        ring_radius: float,
        leg_radius_eff: float,
        leg_spacing: float,
        coil_length: float,
        ring_minor_radius: float,
        phantom_radius: float,
        phantom_height: float,
        port_box_size: Tuple[float, float, float],
        port_radius: float,
        air_padding: float,
        resolution: float,
    ) -> None:
        """Build the birdcage gmsh model on the calling rank (see `birdcage_port_domain`)."""
        gmsh.initialize()
        gmsh.model.add("birdcage_port_domain")

        # Simplified conductor scaffold: two rings plus vertical legs.
        z_ring_offset = 0.5 * leg_spacing
        top_ring = gmsh.model.occ.addTorus(0, 0, z_ring_offset, ring_radius, ring_minor_radius)
        bottom_ring = gmsh.model.occ.addTorus(0, 0, -z_ring_offset, ring_radius, ring_minor_radius)

        leg_tags: List[int] = []
        theta = np.linspace(0.0, 2.0 * np.pi, leg_count, endpoint=False)
        for angle in theta:
            x = ring_radius * np.cos(angle)
            y = ring_radius * np.sin(angle)
            leg = gmsh.model.occ.addCylinder(
                x,
                y,
                -0.5 * coil_length,
                0.0,
                0.0,
                coil_length,
                leg_radius_eff,
            )
            leg_tags.append(leg)

        phantom_tag = gmsh.model.occ.addCylinder(
            0.0,
            0.0,
            -0.5 * phantom_height,
            0.0,
            0.0,
            phantom_height,
            phantom_radius,
        )

        port_dx, port_dy, port_dz = port_box_size
        port_tags: List[int] = []
        for idx, angle in enumerate(theta):
            next_angle = theta[(idx + 1) % leg_count]
            midpoint_angle = np.arctan2(
                np.sin(angle) + np.sin(next_angle),
                np.cos(angle) + np.cos(next_angle),
            )
            cx = port_radius * np.cos(midpoint_angle)
            cy = port_radius * np.sin(midpoint_angle)
            port = gmsh.model.occ.addBox(
                cx - 0.5 * port_dx,
                cy - 0.5 * port_dy,
                -0.5 * port_dz,
                port_dx,
                port_dy,
                port_dz,
            )
            port_tags.append(port)

        radial_extent = ring_radius + max(leg_radius_eff, ring_minor_radius) + port_dy + air_padding
        z_extent = max(0.5 * coil_length, 0.5 * leg_spacing + ring_minor_radius, 0.5 * phantom_height) + air_padding
        air_tag = gmsh.model.occ.addBox(
            -radial_extent,
            -radial_extent,
            -z_extent,
            2.0 * radial_extent,
            2.0 * radial_extent,
            2.0 * z_extent,
        )

        conductor_tags = [top_ring, bottom_ring] + leg_tags

        # GEO-9 step 2b. The previous `occ.cut(..., removeTool=False)` carved the
        # air box around the tools but never booleaned the tools against *each
        # other*: the legs pierce both rings by construction, so those solids
        # overlapped and gmsh failed with "Invalid boundary mesh (overlapping
        # facets) on surface 3 surface 49" (known-issues 7). Fragment the box
        # against ALL tools at once, so every pairwise overlap becomes its own
        # conforming piece, and re-derive the physical groups from the fragment
        # out-map — fragment renumbers and reorders, so absolute tags from before
        # the call mean nothing afterwards.
        tool_tags = conductor_tags + [phantom_tag] + port_tags
        _, fragment_map = gmsh.model.occ.fragment(
            [(3, air_tag)],
            [(3, tag) for tag in tool_tags],
        )
        gmsh.model.occ.synchronize()

        # out-map is positional: one entry per input, objects first then tools.
        input_tags = [air_tag] + tool_tags
        if len(fragment_map) != len(input_tags):
            raise RuntimeError(
                "birdcage_port_domain: occ.fragment returned an out-map of "
                f"{len(fragment_map)} entries for {len(input_tags)} inputs"
            )

        ancestors: Dict[int, set] = {}
        for input_tag, pieces in zip(input_tags, fragment_map):
            for dim, piece in pieces:
                if dim == 3:
                    ancestors.setdefault(piece, set()).add(input_tag)

        conductor_set = set(conductor_tags)
        port_ordinal = {tag: idx for idx, tag in enumerate(port_tags, start=1)}

        # Piece policy. Metal wins over everything (a leg∩ring piece is conductor
        # either way, and a port box grazing a conductor is metal, not an
        # integration volume); the phantom outranks a port box for the same
        # reason. Only pieces descended from a port box alone carry `100+i`, and
        # what is left — descended from the air box only — is air.
        group_of_piece: Dict[int, int] = {}
        for piece, sources in ancestors.items():
            if sources & conductor_set:
                group_of_piece[piece] = 1
            elif phantom_tag in sources:
                group_of_piece[piece] = 3
            elif sources & port_ordinal.keys():
                group_of_piece[piece] = 100 + min(
                    port_ordinal[tag] for tag in sources if tag in port_ordinal
                )
            else:
                group_of_piece[piece] = 2

        pieces_by_group: Dict[int, List[int]] = {}
        for piece, group in sorted(group_of_piece.items()):
            pieces_by_group.setdefault(group, []).append(piece)

        group_names = {1: "conductor", 2: "air", 3: "phantom"}
        for idx in port_ordinal.values():
            group_names[100 + idx] = f"port_P{idx}"

        missing_groups = [
            group_names[tag]
            for tag in [1, 2, 3] + [100 + i for i in port_ordinal.values()]
            if tag not in pieces_by_group
        ]
        volumes = gmsh.model.getEntities(dim=3)
        masses = {tag: gmsh.model.occ.getMass(3, tag) for _, tag in volumes}
        if missing_groups:
            raise RuntimeError(
                "birdcage_port_domain: occ.fragment left no piece for "
                f"{', '.join(missing_groups)}; {len(volumes)} volumes, "
                "per-volume masses [m^3]: "
                + ", ".join(f"tag {tag}: {mass:.6e}" for tag, mass in sorted(masses.items()))
            )

        for group, pieces in sorted(pieces_by_group.items()):
            gmsh.model.addPhysicalGroup(3, pieces, tag=group)
            gmsh.model.setPhysicalName(3, group, group_names[group])

        # Every 3-D entity must carry a marker; a cell with none is exactly what
        # `gmshio.py:118` asserts on. Checked against the model rather than
        # against the out-map, so a piece the out-map never mentioned cannot
        # hide (the `GEO-9` step-1 guard, same reasoning).
        grouped_volumes = set()
        for _, group_tag in gmsh.model.getPhysicalGroups(dim=3):
            grouped_volumes.update(gmsh.model.getEntitiesForPhysicalGroup(3, group_tag))
        ungrouped = sorted({tag for _, tag in volumes} - grouped_volumes)
        if ungrouped:
            raise RuntimeError(
                "birdcage_port_domain: 3-D entities carry no physical group: "
                f"{ungrouped}; {len(volumes)} volumes, masses [m^3]: "
                + ", ".join(f"tag {tag}: {masses[tag]:.6e}" for tag in ungrouped)
            )

        print(
            f"[birdcage-mesh] fragment volumes={len(volumes)} "
            + " ".join(
                f"{group_names[group]}={sum(masses[p] for p in pieces):.6e}"
                f"({len(pieces)}p)"
                for group, pieces in sorted(pieces_by_group.items())
            ),
            flush=True,
        )

        outer_boundary_surfaces = []
        for dim, surf in gmsh.model.getEntities(dim=2):
            x_min, y_min, z_min, x_max, y_max, z_max = gmsh.model.getBoundingBox(dim, surf)
            if (
                abs(abs(x_min) - radial_extent) < resolution
                or abs(abs(x_max) - radial_extent) < resolution
                or abs(abs(y_min) - radial_extent) < resolution
                or abs(abs(y_max) - radial_extent) < resolution
                or abs(abs(z_min) - z_extent) < resolution
                or abs(abs(z_max) - z_extent) < resolution
            ):
                outer_boundary_surfaces.append(surf)

        if outer_boundary_surfaces:
            gmsh.model.addPhysicalGroup(2, outer_boundary_surfaces, tag=1)
            gmsh.model.setPhysicalName(2, 1, "outer_boundary")

        gmsh.model.mesh.setSize(gmsh.model.getEntities(0), resolution)
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.optimize("Netgen")
