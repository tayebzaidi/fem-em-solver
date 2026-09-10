"""Calibration of the per-run memory instrument (`OPS-43` sub-part (c)).

Two asserted gates, both pre-registered in PROJECT_PLAN.md §9 item 4.

**Anchor (closed form — the comparand is the allocation itself).**  Every rank
allocates ``N = 256 MiB`` and touches every page; the rise reported by
:func:`fem_em_solver.utils.instrumentation.summed_peak_rss_bytes` must be
``>= 0.8 * nranks * N`` and ``<= 1.5 * nranks * N``.  An instrument that
reports a constant, the wrong unit (the KiB->bytes factor 1024), or a
rank-local rather than summed figure fails one of the two bounds.

**Negative control.**  ``/sys/fs/cgroup/memory.peak`` is per container lifetime
and read-only on this kernel, so it cannot separate two runs sharing a
container — that is exactly the defect both `xl-ledger.md` rows record.  Here it
is reproduced deliberately at smoke cost: a *large* workload runs first, a
*small* one second, and ``memory.peak`` after the small one is unchanged from
after the large one (it reports the large run's number as the small run's
peak), while summed ``ru_maxrss`` separates the two by >= 2x.

The large-then-small ordering is the point, not an accident: ``memory.peak``
is a high-water mark, so small-then-large could look like it "worked".  Running
the large workload first makes the inherited-peak failure unambiguous.

*Which separation mechanism:* **separate subprocesses**, one per workload, not
separate ``mpiexec`` invocations — ``ru_maxrss`` is a high-water mark over the
whole *process* lifetime, so the small workload could never report a lower
figure than the large one inside this pytest process.  Each rank spawns its own
pair of children; the children are non-MPI processes and call the helper with
``comm=None``.  Trap measured here 2026-09-10: a child of an
``mpiexec``-launched process inherits Hydra's ``PMI_*`` handshake, so importing
``fem_em_solver`` (which eagerly pulls in DolfinX -> mpi4py -> ``MPI_Init``)
aborts with ``PMI_Init failed`` and exit 15.  The child environment is scrubbed
of those prefixes.

Tier: smoke.  No solve, no mesh, no DolfinX import — the anchor needs the
process's baseline RSS to be small compared with 256 MiB.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.utils.instrumentation import (
    format_peak_rss,
    local_peak_rss_bytes,
    summed_peak_rss_bytes,
)

pytestmark = pytest.mark.unit

MIB = 1024 * 1024

#: Anchor allocation per rank.  Comfortably above this process's baseline RSS
#: (pytest + numpy + mpi4py, no DolfinX) so the rise is dominated by it.
ANCHOR_BYTES_PER_RANK = 256 * MIB

#: Pre-registered band on the anchor, PROJECT_PLAN §9 item 4.  Not to be widened.
ANCHOR_LOW_FACTOR = 0.8
ANCHOR_HIGH_FACTOR = 1.5

#: Negative-control workloads, chosen an order of magnitude apart so the >= 2x
#: separation is not a close call.
CONTROL_LARGE_BYTES = 1024 * MIB
CONTROL_SMALL_BYTES = 32 * MIB
CONTROL_SEPARATION_MIN = 2.0

CGROUP_MEMORY_PEAK = Path("/sys/fs/cgroup/memory.peak")

_CHILD_SOURCE = """
import sys
import numpy as np
from fem_em_solver.utils.instrumentation import summed_peak_rss_bytes

nbytes = int(sys.argv[1])
buf = np.empty(nbytes, dtype=np.uint8)
buf[:] = 7  # touch every page; np.empty alone commits nothing
assert int(buf[::4096].sum()) > 0  # keep the allocation live and referenced
print("PEAK_RSS_BYTES", summed_peak_rss_bytes(), flush=True)
"""


#: Environment prefixes Hydra/MPICH export into every rank.  A plain child of an
#: ``mpiexec``-launched process inherits ``PMI_FD``/``PMI_RANK``/``PMI_SIZE``,
#: and importing ``fem_em_solver`` pulls in DolfinX -> mpi4py, which
#: auto-initializes MPI, tries to speak PMI on an fd it does not own and aborts
#: with ``PMI_Init failed`` (exit 15).  Measured 2026-09-10 in this container.
#: The child is a *non-MPI* process by construction, so the job's PMI handshake
#: must not be inherited.
_MPI_ENV_PREFIXES = ("PMI_", "PMIX_", "HYDRA_", "MPICH_", "OMPI_", "MPIEXEC_")


def _child_peak_rss_bytes(nbytes: int) -> int:
    """Run one workload in a fresh, non-MPI process; return its peak RSS bytes."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(_MPI_ENV_PREFIXES)
    }
    src = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD_SOURCE, str(nbytes)],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"child for {nbytes} B exited {proc.returncode}; "
            f"stdout={proc.stdout!r} stderr={proc.stderr[-2000:]!r}"
        )
    for line in proc.stdout.splitlines():
        if line.startswith("PEAK_RSS_BYTES"):
            return int(line.split()[1])
    raise AssertionError(f"child produced no reading; stdout={proc.stdout!r} stderr={proc.stderr!r}")


def _read_memory_peak() -> int:
    return int(CGROUP_MEMORY_PEAK.read_text().strip())


def test_summed_ru_maxrss_tracks_a_known_allocation() -> None:
    """Anchor: the instrument is calibrated against an allocation it chose."""
    comm = MPI.COMM_WORLD
    n = ANCHOR_BYTES_PER_RANK

    comm.Barrier()
    before = summed_peak_rss_bytes(comm)
    before_local = local_peak_rss_bytes()

    buf = np.empty(n, dtype=np.uint8)
    buf[:] = 7  # touch every page
    assert int(buf[::4096].sum()) > 0  # keep it live past the measurement

    comm.Barrier()
    after = summed_peak_rss_bytes(comm)
    after_local = local_peak_rss_bytes()
    rise = after - before

    expected = comm.size * n
    per_rank = comm.gather((comm.rank, before_local, after_local), root=0)
    if comm.rank == 0:
        print(
            "\n[OPS-43(c)] anchor, summed ru_maxrss across "
            f"{comm.size} ranks\n"
            f"    allocation      {format_peak_rss(expected, comm.size)}\n"
            f"    before          {format_peak_rss(before, comm.size)}\n"
            f"    after           {format_peak_rss(after, comm.size)}\n"
            f"    rise            {rise / 2**30:.4f} GiB "
            f"= {rise / expected:.4f} x allocation\n"
            f"    band            [{ANCHOR_LOW_FACTOR}, {ANCHOR_HIGH_FACTOR}] x allocation\n"
            f"    raw per-rank (rank, before_B, after_B): {per_rank}",
            flush=True,
        )

    assert rise >= ANCHOR_LOW_FACTOR * expected, (
        f"summed ru_maxrss rose {rise} B for a {expected} B allocation "
        f"({rise / expected:.4f} x) — below the pre-registered "
        f"{ANCHOR_LOW_FACTOR} x floor; per-rank raw values {per_rank}"
    )
    assert rise <= ANCHOR_HIGH_FACTOR * expected, (
        f"summed ru_maxrss rose {rise} B for a {expected} B allocation "
        f"({rise / expected:.4f} x) — above the pre-registered "
        f"{ANCHOR_HIGH_FACTOR} x ceiling; per-rank raw values {per_rank}"
    )


@pytest.mark.skipif(
    not CGROUP_MEMORY_PEAK.exists(),
    reason="no /sys/fs/cgroup/memory.peak (cgroup v2 only)",
)
def test_memory_peak_cannot_separate_two_runs_but_ru_maxrss_can() -> None:
    """Negative control: reproduce the xl-ledger defect at smoke cost."""
    comm = MPI.COMM_WORLD

    # Barriers align the phases across ranks so one rank's large child cannot
    # inflate the container peak while another rank is timing its small child.
    comm.Barrier()
    peak_before = _read_memory_peak()

    comm.Barrier()
    large_rss = _child_peak_rss_bytes(CONTROL_LARGE_BYTES)  # large FIRST
    comm.Barrier()
    peak_after_large = _read_memory_peak()

    comm.Barrier()
    small_rss = _child_peak_rss_bytes(CONTROL_SMALL_BYTES)  # small SECOND
    comm.Barrier()
    peak_after_small = _read_memory_peak()

    summed_large = comm.allreduce(large_rss, op=MPI.SUM)
    summed_small = comm.allreduce(small_rss, op=MPI.SUM)
    ratio = summed_large / summed_small

    if comm.rank == 0:
        print(
            "\n[OPS-43(c)] negative control — separate subprocesses, "
            "large run first then small, one container lifetime\n"
            f"    memory.peak before        {peak_before} B "
            f"({peak_before / 2**30:.4f} GiB)\n"
            f"    memory.peak after large   {peak_after_large} B "
            f"({peak_after_large / 2**30:.4f} GiB)\n"
            f"    memory.peak after small   {peak_after_small} B "
            f"({peak_after_small / 2**30:.4f} GiB)  <- indistinguishable\n"
            f"    summed ru_maxrss large    {summed_large} B "
            f"({summed_large / 2**30:.4f} GiB)\n"
            f"    summed ru_maxrss small    {summed_small} B "
            f"({summed_small / 2**30:.4f} GiB)\n"
            f"    separation                {ratio:.4f} x "
            f"(floor {CONTROL_SEPARATION_MIN} x)\n"
            f"    raw per-rank (rank, large_B, small_B): "
            f"{comm.gather((comm.rank, large_rss, small_rss), root=0)}",
            flush=True,
        )
    else:
        comm.gather((comm.rank, large_rss, small_rss), root=0)

    assert peak_after_large >= peak_before, (
        "memory.peak is a high-water mark and must not decrease: "
        f"{peak_before} -> {peak_after_large}"
    )
    assert peak_after_small == peak_after_large, (
        "memory.peak separated the small run from the large one "
        f"({peak_after_large} -> {peak_after_small}); this control asserts it "
        "cannot, because it is a per-container-lifetime high-water mark. A "
        "change here means something else in the container allocated during "
        "the small phase, not that memory.peak became attributable."
    )
    assert ratio >= CONTROL_SEPARATION_MIN, (
        f"summed ru_maxrss separated the two runs by only {ratio:.4f} x "
        f"(floor {CONTROL_SEPARATION_MIN} x): large {summed_large} B, "
        f"small {summed_small} B"
    )
