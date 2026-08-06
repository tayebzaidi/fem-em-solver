"""`POST-1` step 6: CSV export and the stats path must sample the same cells.

``export_tagged_field_samples_csv`` and ``compute_tagged_vector_magnitude_stats``
both call ``_sampling_cells_with_interface_guardrails`` and then
``_evaluate_on_cells``, but nothing has ever gated one against the other.  Step 5
flipped both defaults to ``prefer_interior_samples=False`` in one commit; a later
divergence — one path regaining the guardrail, acquiring a filter, or losing the
owned-cell restriction — would be silent, and the CSV is the artefact the human
operator reads.

The anchor is an integer identity plus a float identity, on step 1's 12³
piecewise-σ fixture:

* the number of data rows written to the CSV equals ``stats["count"]``
  **exactly** (the export gathers every rank's samples to rank 0, so the row
  count is already the global count);
* ``min``/``max``/``mean`` of the CSV's ``mag`` column equal the allreduced
  statistics to ``1e-12`` relative.  Both paths compute ``|F| = sqrt(Σ|F_i|²)``
  off the same evaluation, so the only spread available is CSV float
  round-trip — and ``csv.writer`` formats a float with ``str``, which is the
  shortest round-tripping representation, so the round-trip is exact.  The probe
  below measures that before anything is gated.

The negative control is the retired sampling rule: ``prefer_interior_samples=
True`` passed to *both* paths must reproduce the guarded count, short of the
default by exactly the number of boundary-adjacent tagged cells the guardrail
drops (288 per tag on this fixture at ``-n 2``, step 5's integer identity).  The
two paths must agree in **both** modes, or agreement in the default mode is
coincidence rather than shared sampling.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/post/test_csv_export_stats_parity.py -v -s'
"""

from __future__ import annotations

import csv

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.post.phantom_fields import (
    _interior_tagged_cells,
    _tagged_cells,
    compute_tagged_vector_magnitude_stats,
    export_tagged_field_samples_csv,
)

from tests.complex_mode import complex_only
from tests.post.test_phantom_phasor_semantics import (
    FIXTURE_N,
    _solve_two_material_fixture,
)
from tests.validation.test_poynting_balance import TAG_HIGH, TAG_LOW

# Both paths reduce the same magnitudes; the CSV round-trip through ``str`` is
# exact for float64, so this is round-off head-room, not a physics band.  The
# probe test prints the measured disagreement — set from measurement, never
# widened after the fact.
IDENTITY_RTOL = 1e-12

TAGS = (TAG_LOW, TAG_HIGH)
PREFER_INTERIOR = (False, True)


@pytest.fixture(scope="module")
def piecewise_sigma_field():
    """Step 1's fixture, unchanged: one 12³ piecewise-σ complex solve."""
    return _solve_two_material_fixture(FIXTURE_N)


def _export_and_read(field, cell_tags, tag, tmp_path, comm, *, prefer_interior):
    """Export the CSV and parse it on rank 0; returns ``None`` off rank 0.

    The export writes on rank 0 only (it gathers there), so the read happens on
    rank 0 after a barrier — establishing the write is complete before any rank
    looks at the file.
    """
    path = tmp_path / f"samples_tag{tag}_prefer{int(prefer_interior)}.csv"
    written = export_tagged_field_samples_csv(
        field,
        cell_tags,
        tag,
        path,
        comm=comm,
        prefer_interior_samples=prefer_interior,
    )
    comm.Barrier()

    if comm.rank != 0:
        assert written is None, "a non-zero rank returned a path from the CSV export"
        return None

    assert written == path
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    header, data = rows[0], rows[1:]
    columns = {name: np.asarray([float(r[i]) for r in data]) for i, name in enumerate(header)}
    return {"header": header, "n_rows": len(data), "columns": columns}


def _component_magnitudes(columns) -> np.ndarray:
    """Recompute ``|F|`` from the CSV's component columns.

    Independent of the ``mag`` column: if the export ever wrote ``Re`` where the
    phasor magnitude belongs (`POST-3` step 4's defect), this catches it.
    """
    if "fx_re" in columns:
        components = [
            columns[f"f{axis}_re"] + 1j * columns[f"f{axis}_im"] for axis in ("x", "y", "z")
        ]
    else:
        components = [columns[f"f{axis}"] for axis in ("x", "y", "z")]
    return np.sqrt(sum(np.abs(c) ** 2 for c in components))


@complex_only
@pytest.mark.integration
def test_probe_csv_round_trip_precision(piecewise_sigma_field, tmp_path):
    """Probe: what precision does the CSV format actually carry?

    Sizes the float identity before it is gated.  Printed, then asserted only
    against the loose ceiling the plan allowed (1e-12) — the tight gates below
    are set from what this measures.
    """
    comm = MPI.COMM_WORLD
    e_field, cell_tags = piecewise_sigma_field

    worst = 0.0
    lines = []
    for tag in TAGS:
        stats = compute_tagged_vector_magnitude_stats(e_field, cell_tags, tag, comm=comm)
        parsed = _export_and_read(
            e_field, cell_tags, tag, tmp_path, comm, prefer_interior=False
        )
        if comm.rank != 0:
            continue
        mag = parsed["columns"]["mag"]
        csv_stats = {"min": float(mag.min()), "max": float(mag.max()), "mean": float(mag.mean())}
        lines.append(f"  tag {tag}: header {parsed['header']}")
        lines.append(f"    rows {parsed['n_rows']}  stats count {stats['count']}")
        for key in ("min", "max", "mean"):
            rel = abs(csv_stats[key] - stats[key]) / abs(stats[key])
            worst = max(worst, rel)
            lines.append(
                f"    {key:<5}: csv {csv_stats[key]!r:>24}  stats {stats[key]!r:>24}  rel {rel:.3e}"
            )
        recomputed = _component_magnitudes(parsed["columns"])
        rel_col = float(np.max(np.abs(recomputed - mag) / np.abs(mag)))
        worst = max(worst, rel_col)
        lines.append(f"    mag vs components: worst rel {rel_col:.3e}")

    if comm.rank == 0:
        print(f"\n[POST-1 step 6] probe at -n {comm.size}:")
        print("\n".join(lines), flush=True)
        print(f"  worst relative disagreement over all quantities: {worst:.3e}", flush=True)
        assert worst < IDENTITY_RTOL, (
            f"CSV round-trip carries only {worst:.3e} relative precision; the "
            f"{IDENTITY_RTOL:.0e} gates below are not attainable on this format"
        )


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("tag", TAGS)
@pytest.mark.parametrize("prefer_interior", PREFER_INTERIOR)
def test_csv_rows_match_the_stats_sample_set(
    piecewise_sigma_field, tag, prefer_interior, tmp_path
):
    """Anchor: row count == ``stats["count"]`` exactly, mag statistics to 1e-12.

    Parametrised over **both** sampling modes: agreement in the production
    default alone would not distinguish "the two paths share a sampling rule"
    from "the two paths happen to have the same default".
    """
    comm = MPI.COMM_WORLD
    e_field, cell_tags = piecewise_sigma_field

    stats = compute_tagged_vector_magnitude_stats(
        e_field, cell_tags, tag, comm=comm, prefer_interior_samples=prefer_interior
    )
    parsed = _export_and_read(
        e_field, cell_tags, tag, tmp_path, comm, prefer_interior=prefer_interior
    )
    if comm.rank != 0:
        return

    mag = parsed["columns"]["mag"]
    print(
        f"\n[POST-1 step 6] tag {tag}, prefer_interior={prefer_interior}, -n {comm.size}: "
        f"csv rows {parsed['n_rows']}, stats count {stats['count']}",
        flush=True,
    )
    for key, value in (("min", mag.min()), ("max", mag.max()), ("mean", mag.mean())):
        print(f"  {key:<5}: csv {float(value)!r:>24}  stats {stats[key]!r:>24}", flush=True)

    assert parsed["n_rows"] == stats["count"], (
        f"the CSV holds {parsed['n_rows']} rows where the stats path counted "
        f"{stats['count']} samples at -n {comm.size}: the two entry points are "
        "not sampling the same cells"
    )
    for key, value in (("min", mag.min()), ("max", mag.max()), ("mean", mag.mean())):
        assert np.isclose(float(value), stats[key], rtol=IDENTITY_RTOL, atol=0.0), (
            f"CSV '{key}' = {float(value):.15e} vs stats {stats[key]:.15e} — the "
            "exported samples are not the samples the statistics were reduced over"
        )

    # The ``mag`` column is the phasor magnitude of the components beside it,
    # not ``Re`` of anything (`POST-3` step 4).
    recomputed = _component_magnitudes(parsed["columns"])
    assert np.allclose(recomputed, mag, rtol=IDENTITY_RTOL, atol=0.0), (
        f"worst |F| disagreement {np.max(np.abs(recomputed - mag) / np.abs(mag)):.3e} "
        "between the CSV's mag column and its own component columns"
    )


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("tag", TAGS)
def test_guarded_export_is_short_by_exactly_the_dropped_layer(
    piecewise_sigma_field, tag, tmp_path
):
    """Negative control: the retired rule, reproduced through the export.

    ``prefer_interior_samples=True`` must drop the boundary-adjacent tagged
    cells from the *CSV* too, and by exactly the count the guardrail computes
    (288 per tag on this fixture at ``-n 2``, step 5).  If the difference were 0
    the two modes would be indistinguishable here and the parametrised gate
    above would prove nothing about the sampling rule.
    """
    comm = MPI.COMM_WORLD
    e_field, cell_tags = piecewise_sigma_field
    mesh = e_field.function_space.mesh

    default = _export_and_read(
        e_field, cell_tags, tag, tmp_path, comm, prefer_interior=False
    )
    guarded = _export_and_read(
        e_field, cell_tags, tag, tmp_path, comm, prefer_interior=True
    )
    interior = _interior_tagged_cells(mesh, cell_tags, tag)
    n_dropped = comm.allreduce(
        int(_tagged_cells(cell_tags, tag).size - interior.size), op=MPI.SUM
    )
    if comm.rank != 0:
        return

    print(
        f"\n[POST-1 step 6] negative control, tag {tag}, -n {comm.size}: default rows "
        f"{default['n_rows']}, guarded rows {guarded['n_rows']}, guardrail drops "
        f"{n_dropped}",
        flush=True,
    )

    assert n_dropped > 0, (
        f"the guardrail drops no cell of tag {tag} at -n {comm.size}; the two "
        "sampling modes coincide, so the export cannot be seen to follow either"
    )
    assert default["n_rows"] - guarded["n_rows"] == n_dropped, (
        f"the guarded export wrote {guarded['n_rows']} rows, "
        f"{default['n_rows'] - guarded['n_rows']} fewer than the default, not the "
        f"{n_dropped} boundary-adjacent cells the guardrail drops: the export does "
        "not honour the sampling rule it is passed"
    )
