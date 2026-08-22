"""Example (`EX-27`): region-resolution policy on the coil+phantom mesh.

The example angle `GEO-17` owes. That chunk's subject is not a field and not a
geometry — it is a **mesh sizing policy**: asking `coil_phantom_domain` for a
per-region characteristic length (coil 0.012 m, phantom 0.010 m, air 0.020 m)
instead of one global 0.015 m. `GEO-17` step 1 (2026-08-20) found the policy
was never applied at all — the region point walk used
``gmsh.model.getBoundary``'s default ``combined=True``, whose result for a
volume's closed shell is empty, so every region collected zero points and
``mesh.setSize`` was never called. Only the global ``CharacteristicLengthMin/Max``
clamps survived, and under the policy those clamps are ``[0.010, 0.020]`` — so
the "refined" coil was actually meshed at the **air's** 0.020 ceiling and lost
21.68% / 22.62% of its volume. The fix is a ``Min`` over four per-volume
``Constant`` size fields. This script builds the same CAD both ways and asserts
the difference.

**The quantity.** Not "does it look finer": the fraction of each curved region's
**analytic CAD volume** that survives into the mesh — two tori ``2 pi^2 R r^2``
and a cylinder ``pi r^2 h``. A linear-tet mesh *inscribes* a curved surface, so
this ratio is bounded above by 1 and rises monotonically with refinement. That
makes the sign of the move an identity rather than a band, which is exactly what
`GEO-17` step 1 replaced its old 5% band with (the band's premise — "region
sizing must not move the geometry" — is false for a curved region, and would now
*reject* a correct mesh).

* **policy** (`Min` over per-volume Constant fields): coil recovery >=
  ``POLICY_MIN_CAD_RECOVERY`` (0.755), the floor `GEO-17` step 1 pre-registered.
  On record: **0.835563 / 0.833730**.
* **clamps-only** (the same call with no per-region sizes — one global 0.015):
  asserted *to fail* the same 0.755 floor, the `EX-18`/`EX-20` inverted-assertion
  pattern. On record: **0.754685 / 0.752565**, and this control is thin *by
  construction* — the floor was chosen as "the uniform mesh's own recovery,
  which a finer request must beat", so it sits ~3.2e-4 above the control. The
  separation that actually discriminates is between the two *sizings*
  (**+0.0809 / +0.0812**), and that is gated separately at
  ``SIZING_SEPARATION``.

Every number above that is a gate is **imported** from the `GEO-17` module that
gated it (`tests/mesh/test_mesh_tag_integrity.py`, the `ANS-1` rule): the
geometry, the policy sizes, the 0.755 floor, the refined-tag list, the CAD
volumes, and the `OPS-17` uniform-volume record. The two *recovery* records are
restated here with provenance, because the gate holds them as printed output
rather than as named constants (the `EX-26` precedent).

**Also re-asserted, unmoved:** the tagged-volume partition identity on *both*
meshes — the four tags sum to the mesh volume to ``VOLUME_PARTITION_BAND``
(1e-9) — and the `OPS-17` uniform-sizing volume table to 1e-9. A sizing policy
changes element sizes, not the partition: an identity that moves means a region
lost its physical group or got meshed twice, which is a defect in the size field
rather than a resolution effect.

**Mesh only — no solve, no SAR claim.** This demonstrates the mesh capability
`MAT-4`'s SAR-on-a-coil route runs through, and nothing downstream of it; the
script needs only the real DolfinX build.

Run it through the example runner::

    ./run_examples.sh -e mesh:5

Output lands in ``examples/meshing/paraview_output/``: open
``region_resolution_policy_clamps_only_combined.xdmf`` and
``region_resolution_policy_policy_combined.xdmf`` side by side and threshold on
``CellTags`` (1 = coil_1, 2 = coil_2, 3 = phantom, 4 = air). The tori are
visibly faceted in the clamps-only mesh and round in the policy mesh, while the
air is coarser — that trade is the point of the example.

Measured 2026-08-22 at ``-n 2``: clamps-only 19 792 cells / 2.89 s mesh, policy
20 843 cells / 2.38 s mesh; coil meshed/CAD **0.754685 -> 0.835563** and
**0.752565 -> 0.833730**, separations **+0.080879 / +0.081165**; 5.4 s in-script
total including both exports (8 s of harness wall clock — commissioned standard,
measured smoke). Volumes and ratios are bit-identical to the `GEO-17` records;
only the wall times move.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from mpi4py import MPI

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH, so the repo root goes on
# sys.path: the gate, the policy sizes and the fixture geometry live in the
# `GEO-17` test module and are imported, never restated (`ANS-1`).
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402
from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)

from tests.mesh.helpers import (  # noqa: E402
    REQUIRED_COIL_PHANTOM_TAGS,
    VOLUME_PARTITION_BAND,
    assert_tag_volumes_partition_domain,
)
from tests.mesh.test_mesh_tag_integrity import (  # noqa: E402
    CAD_VOLUMES,
    GEOMETRY,
    POLICY_MIN_CAD_RECOVERY,
    POLICY_RESOLUTIONS,
    REFINED_TAGS,
    UNIFORM_VOLUMES_RECORD,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "region_resolution_policy"

# The two coil tags, the regions the policy refines *and* whose CAD volume is a
# torus — the phantom (tag 3) is a cylinder and starts at 0.98 recovery, so it
# does not discriminate between the two sizings.
COIL_TAGS = (1, 2)

# `GEO-17` step 1's measured recoveries, from
# `20260820T110549Z_GEO-17-step1-final.log` (the record-bearing run; the
# probe-defaults log carries the same figures). Restated rather than imported
# because the gate holds them as printed output, not as named constants — the
# `EX-26` precedent. Reproduced here inside RECORD_BAND.
POLICY_RECOVERY_RECORD = {1: 0.835563, 2: 0.833730}
RECORD_BAND = 0.01  # 1%, pre-stated in the EX-27 commission

# The clamps-only mesh recovers 0.754685 / 0.752565, but that is not restated:
# it is UNIFORM_VOLUMES_RECORD[tag] / CAD_VOLUMES[tag], both imported, so the
# control's own record is derived from the gate's constants.

# The gap the example actually needs to be real. The inverted control (uniform
# missing the 0.755 floor) clears by ~3.2e-4 by construction, so on its own it
# would pass even if the policy did almost nothing. Pre-stated at 0.05;
# measured +0.0809 (coil_1) and +0.0812 (coil_2).
SIZING_SEPARATION = 0.05


def _build(label, comm, **resolutions):
    """One sizing: mesh, tags, tagged volumes (partition-gated), wall time."""
    started = time.perf_counter()
    mesh, cell_tags, _ = MeshGenerator.coil_phantom_domain(
        comm=comm, **resolutions, **GEOMETRY
    )
    elapsed = time.perf_counter() - started

    # Gates the 1e-9 partition identity on this mesh and returns the per-tag
    # volumes; every reduction inside is global, so nothing here is rank-local.
    volumes = assert_tag_volumes_partition_domain(
        mesh,
        cell_tags,
        REQUIRED_COIL_PHANTOM_TAGS,
        comm=comm,
        label=f"EX-27 {label}",
    )

    return {
        "label": label,
        "mesh": mesh,
        "cell_tags": cell_tags,
        "n_cells": mesh.topology.index_map(3).size_global,
        "mesh_wall_time_s": elapsed,
        "v": volumes,
    }


def _write_paraview(build, comm):
    """Mesh + cell tags of one sizing, as a DG0 ``CellTags`` array."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_{build['label']}_combined",
        build["mesh"],
        build["cell_tags"],
        {},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if comm.rank == 0:
        print("=" * 72)
        print("EX-27 — coil+phantom fixture: region-resolution policy vs clamps only")
        print("=" * 72)
        print(
            f"\n[geometry] coil R={GEOMETRY['coil_major_radius']} m "
            f"r={GEOMETRY['coil_minor_radius']} m  separation="
            f"{GEOMETRY['coil_separation']} m"
            f"\n[geometry] phantom {GEOMETRY['phantom_radius']} x "
            f"{GEOMETRY['phantom_height']} m  air_padding={GEOMETRY['air_padding']} m"
            f"\n[mesh]     clamps only: one global resolution="
            f"{GEOMETRY['resolution']} m"
            f"\n[mesh]     policy     : "
            + "  ".join(f"{k.split('_')[0]}={v}" for k, v in POLICY_RESOLUTIONS.items())
            + " m"
            f"\n[gate]     policy coil meshed/CAD >= {POLICY_MIN_CAD_RECOVERY}; "
            "clamps-only asserted to FAIL it",
            flush=True,
        )

    # ---- sizing 1: the negative control, built first ----------------------
    clamps = _build("clamps_only", comm)

    # ---- sizing 2: the policy that carries the gate -----------------------
    policy = _build("policy", comm, **POLICY_RESOLUTIONS)

    recovery = {
        build["label"]: {tag: build["v"][tag] / cad for tag, cad in CAD_VOLUMES.items()}
        for build in (clamps, policy)
    }

    if comm.rank == 0:
        print(
            f"\n[EX-27] partition identity holds on both meshes to "
            f"{VOLUME_PARTITION_BAND:.0e} (printed above)\n"
        )
        for build in (clamps, policy):
            print(
                f"  {build['label']:<12s} cells={build['n_cells']:>8d}  "
                f"mesh={build['mesh_wall_time_s']:6.2f} s"
            )
        print("\n[GEO-17] tagged volumes, clamps-only -> policy:")
        for tag, name in sorted(REQUIRED_COIL_PHANTOM_TAGS.items()):
            v_u, v_p = clamps["v"][tag], policy["v"][tag]
            print(
                f"  tag {tag} ({name:<8s}) {v_u:.9e} -> {v_p:.9e} m^3  "
                f"({v_p / v_u - 1.0:+.4%})"
            )
        print("\n[GEO-17] meshed/CAD recovery (linear tets inscribe, so <= 1):")
        for tag, cad in sorted(CAD_VOLUMES.items()):
            name = REQUIRED_COIL_PHANTOM_TAGS[tag]
            print(
                f"  tag {tag} ({name:<8s}) CAD {cad:.9e} m^3  "
                f"clamps {recovery['clamps_only'][tag]:.6f} -> "
                f"policy {recovery['policy'][tag]:.6f}  "
                f"(separation {recovery['policy'][tag] - recovery['clamps_only'][tag]:+.6f})"
            )
        print(flush=True)

    # ---- negative control (a): the fix may not move the clamps-only path ---
    # `OPS-17`'s recorded uniform table, known-issues "Four defects" §1,
    # `20260817T111054Z_OPS-17-step2-mesh-n2.log`.
    for tag, v_recorded in UNIFORM_VOLUMES_RECORD.items():
        rel = abs(clamps["v"][tag] / v_recorded - 1.0)
        assert rel < VOLUME_PARTITION_BAND, (
            f"clamps-only sizing moved tag {tag} "
            f"({REQUIRED_COIL_PHANTOM_TAGS[tag]}) by {rel:.3e} against its "
            f"OPS-17 record: {v_recorded:.9e} -> {clamps['v'][tag]:.9e} m^3"
        )

    # ---- negative control (b): the same measurement must FAIL the gate -----
    for tag in COIL_TAGS:
        assert recovery["clamps_only"][tag] < POLICY_MIN_CAD_RECOVERY, (
            f"clamps-only mesh recovers {recovery['clamps_only'][tag]:.6f} of tag "
            f"{tag} ({REQUIRED_COIL_PHANTOM_TAGS[tag]})'s CAD volume, clearing the "
            f"{POLICY_MIN_CAD_RECOVERY} floor the policy is supposed to be needed "
            "for (on record: 0.754685 / 0.752565). The control no longer "
            "separates — the premise needs re-examining, not the floor."
        )

    # ---- the gate: the policy clears the floor, at both records ------------
    for tag in COIL_TAGS:
        name = REQUIRED_COIL_PHANTOM_TAGS[tag]
        assert recovery["policy"][tag] >= POLICY_MIN_CAD_RECOVERY, (
            f"policy mesh recovers only {recovery['policy'][tag]:.6f} of tag {tag} "
            f"({name})'s CAD volume, below the pre-stated "
            f"{POLICY_MIN_CAD_RECOVERY}. Record the measured frontier in the "
            "EX-27 entry rather than moving the floor."
        )
        drift = abs(recovery["policy"][tag] / POLICY_RECOVERY_RECORD[tag] - 1.0)
        assert drift < RECORD_BAND, (
            f"policy recovery on tag {tag} ({name}) is {recovery['policy'][tag]:.6f} "
            f"against the GEO-17 record {POLICY_RECOVERY_RECORD[tag]:.6f} — a drift "
            f"of {drift:.3e}, outside the pre-stated {RECORD_BAND:.0%} band"
        )

    # ---- the identity: refinement can only move meshed volume up ----------
    for tag in REFINED_TAGS:
        name = REQUIRED_COIL_PHANTOM_TAGS[tag]
        assert policy["v"][tag] > clamps["v"][tag], (
            f"the policy asked for a FINER size on tag {tag} ({name}) and the "
            f"meshed volume did not grow: {clamps['v'][tag]:.9e} -> "
            f"{policy['v'][tag]:.9e} m^3. A linear-tet mesh inscribes a curved "
            "surface, so refinement can only move meshed volume up toward CAD"
        )
    # ... and the one region the policy *coarsens* is the one that pays for it.
    assert policy["v"][4] < clamps["v"][4], (
        f"the policy coarsens the air (0.015 -> {POLICY_RESOLUTIONS['air_resolution']}) "
        f"and its meshed volume did not shrink: {clamps['v'][4]:.9e} -> "
        f"{policy['v'][4]:.9e} m^3 — the volume the refined regions gain has to "
        "come from somewhere"
    )

    # ---- and both stay under the inscription bound ------------------------
    for label in ("clamps_only", "policy"):
        for tag, cad in CAD_VOLUMES.items():
            assert recovery[label][tag] <= 1.0, (
                f"{label} mesh recovers {recovery[label][tag]:.6f} of tag {tag} "
                f"({REQUIRED_COIL_PHANTOM_TAGS[tag]})'s CAD volume {cad:.9e} m^3 "
                "— an inscribing linear-tet mesh cannot exceed 1.0"
            )

    # ---- the separation that makes the control mean something -------------
    for tag in COIL_TAGS:
        separation = recovery["policy"][tag] - recovery["clamps_only"][tag]
        assert separation >= SIZING_SEPARATION, (
            f"tag {tag} ({REQUIRED_COIL_PHANTOM_TAGS[tag]}) separates the two "
            f"sizings by only {separation:.6f}, under the pre-stated "
            f"{SIZING_SEPARATION} (on record: +0.0809 / +0.0812). The floor sits "
            "3.2e-4 above the control, so without this margin the example would "
            "pass on a policy that did essentially nothing."
        )

    # ---- ParaView ---------------------------------------------------------
    written = {build["label"]: _write_paraview(build, comm) for build in (clamps, policy)}
    if comm.rank == 0:
        print("[paraview] wrote:")
        for what, path in written.items():
            print(f"  {what:<12s} {path}")
        print(
            "\n[paraview] threshold `CellTags` in each file "
            + ", ".join(f"{t} = {n}" for t, n in sorted(REQUIRED_COIL_PHANTOM_TAGS.items()))
            + ";"
            "\n           open both side by side — the tori are faceted under the"
            "\n           clamps and round under the policy, and the air is coarser."
            f"\n\nAll identities hold. Total elapsed {time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
