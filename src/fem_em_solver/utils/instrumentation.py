"""Per-run memory instrumentation: summed ``ru_maxrss`` across MPI ranks.

`OPS-43` sub-part (c).  The XL ledger's memory column is unusable twice over
(``docs/testing/xl-ledger.md``): `ANS-4` step 2b's figure is a ``docker stats``
spot reading rather than a peak, and `TH-11` step 5d's is
``/sys/fs/cgroup/memory.peak`` over a *container lifetime that spans a killed
earlier attempt*, so it is a maximum over two runs and is not attributable to
either.  ``memory.peak`` is per container lifetime and read-only on this
kernel; it cannot be zeroed between runs, so a second run in the same container
inherits the first run's high-water mark and reports it as its own.

``resource.getrusage(RUSAGE_SELF).ru_maxrss`` is per *process*, so a fresh
``mpiexec`` invocation gets a fresh instrument.  Summed over the ranks of one
job it is the job's peak resident footprint, which is the number an XL
commissioning actually needs.

Two facts this module pins down rather than leaving at each call site:

* ``ru_maxrss`` is in **KiB on Linux** and in bytes on macOS.  This box is
  Linux; the module refuses to run anywhere else rather than porting the
  ambiguity.  The 1024 factor is the obvious defect, and the calibration test
  in ``tests/unit/test_memory_instrument.py`` catches it.
* the allreduce is a **collective** — every rank of ``comm`` must call
  :func:`summed_peak_rss_bytes`, or the job hangs to its ``timeout``.

``ru_maxrss`` is a high-water mark over the whole process lifetime, so it
cannot fall: a small phase following a large one inside *one* process still
reports the large figure.  Comparing two workloads therefore needs two
processes (two ``mpiexec`` invocations, or a subprocess each).
"""

from __future__ import annotations

import resource
import sys

__all__ = [
    "KIB",
    "local_peak_rss_bytes",
    "summed_peak_rss_bytes",
    "format_peak_rss",
    "report_peak_rss",
]

#: ``ru_maxrss`` unit on Linux.  Not a platform-dependent constant here on
#: purpose — see the module docstring.
KIB = 1024


def _require_linux() -> None:
    if not sys.platform.startswith("linux"):
        raise RuntimeError(
            "fem_em_solver.utils.instrumentation assumes ru_maxrss is in KiB, "
            f"which holds on Linux; this is {sys.platform!r}.  Fix the unit "
            "here deliberately rather than at a call site."
        )


def local_peak_rss_bytes() -> int:
    """Peak resident set size of *this process*, in bytes.

    High-water mark over the process lifetime; it never decreases.
    """
    _require_linux()
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * KIB


def summed_peak_rss_bytes(comm=None) -> int:
    """Peak RSS summed over the ranks of ``comm``, in bytes.

    ``comm=None`` returns the local figure unreduced, which is what a
    single-process child (or a probe script run outside ``mpiexec``) wants.

    **Collective** when ``comm`` is given: every rank must call it.
    """
    local = local_peak_rss_bytes()
    if comm is None:
        return local
    from mpi4py import MPI

    return int(comm.allreduce(local, op=MPI.SUM))


def format_peak_rss(total_bytes: int, nranks: int = 1) -> str:
    """One-line human form: GiB total, and the per-rank average."""
    gib = total_bytes / 2**30
    if nranks > 1:
        return f"{gib:.4f} GiB summed over {nranks} ranks ({gib / nranks:.4f} GiB/rank)"
    return f"{gib:.4f} GiB"


def report_peak_rss(comm=None, label: str = "peak RSS") -> int:
    """Reduce and print rank-0-only; returns the summed figure on every rank.

    Collective when ``comm`` is given.  The print is rank-0-only so an
    ``-n 16`` window does not carry sixteen copies of the same line, but the
    return value is valid on every rank (``allreduce``, not ``reduce``).
    """
    total = summed_peak_rss_bytes(comm)
    nranks = 1 if comm is None else comm.size
    if comm is None or comm.rank == 0:
        print(f"[mem] {label}: {format_peak_rss(total, nranks)}", flush=True)
    return total
