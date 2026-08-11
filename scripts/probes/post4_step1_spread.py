"""`POST-4` step 1 anchor: cross-rank-count analysis of the three probe logs.

Parses the ``MESH_FINGERPRINT`` / ``CLAIM`` / ``VALUES`` lines that
``scripts/probes/post4_step1_probe.py`` emits at ``-n 1``, ``-n 2`` and
``-n 4`` and reports the four things the diagnosis turns on:

1. **mesh identity** — the three runs must share a mesh, or nothing downstream
   is comparable;
2. **the ownership census** — claim multiplicity, distinct claiming *global*
   cells, cross-cell disagreement, and ``valid_mask``, per point per rank count.
   The suspect mechanism (``links[0]`` + last-writer-wins in
   ``evaluate_vector_field_parallel``) can only bite where a point is claimed by
   more than one cell;
3. **the rank spread per field** — ``|a - b| / max(|a|, |b|)`` over the rank
   pairs, for the Lagrange interpolants the example samples (``E_lag``,
   ``B_lag``) and for the source fields they were interpolated from (``E_src``,
   ``B_src``);
4. **the ε-nudge** — the same points at x = y = 1e-6 m.

The attribution identity: if the census is empty (no multi-claims, no mask
holes, zero cross-cell disagreement) *and* the source fields are rank-stable at
the very points where the interpolants spread, the point-evaluation ownership
tie-break is refuted and the locus is the interpolation into Lagrange P1.

Run through the harness::

    scripts/testing/run_and_log.sh POST-4 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && timeout 30 python3 scripts/probes/post4_step1_spread.py'"
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LOGS = Path("docs/testing/logs")
RUNS = {
    "n1": "20260811T140414Z_POST-4-step1-n1.log",
    "n2": "20260811T140345Z_POST-4-step1-n2.log",
    "n4": "20260811T140402Z_POST-4-step1-n4.log",
}
FIELDS = ["E_lag", "B_lag", "E_src", "B_src"]
SETS = ["axis", "nudge"]

FINGERPRINT = re.compile(r"MESH_FINGERPRINT cells=(\d+) m1=([\d.e+-]+) m2=([\d.e+-]+)")
VALUES = re.compile(r"VALUES (\w+) (\w+) (.+)")
CLAIM = re.compile(
    r"CLAIM (\w+) (\w+)\s+(\d+) z=([+-][\d.]+) nranks=(\d+) ncells=(\d+) "
    r"valid=(\w+) maxcross=([\d.e+-]+) libmag=(?:[\d.e+-]+)"
)

# EX-16's record on this fixture, cited not recomputed
# (20260810T170457Z_EX-16-spread-v2.log): the centerline's -n 2 vs -n 4 spread
# and, as the positive control, the 493-point phantom-region sampler's spread
# over the same two solves and the same fields.
EX16_CENTERLINE = 0.235539
EX16_PHANTOM = 0.00007326
# The step-1 anchor: interpolant-path spread must exceed source-path spread by
# at least the 235x the chunk entry names for the (refuted) nudge collapse.
SEPARATION_MIN = 235.0


def parse(name: str):
    text = (LOGS / name).read_text()
    fp = FINGERPRINT.search(text)
    assert fp, f"{name}: no MESH_FINGERPRINT line"
    values = {
        (s, f): [float(v) for v in rest.split()] for s, f, rest in VALUES.findall(text)
    }
    claims = [
        {
            "set": s, "field": f, "i": int(i), "z": float(z), "nranks": int(nr),
            "ncells": int(nc), "valid": v == "True", "maxcross": float(mx),
        }
        for s, f, i, z, nr, nc, v, mx in CLAIM.findall(text)
    ]
    expected = len(SETS) * len(FIELDS)
    assert len(values) == expected, f"{name}: expected {expected} VALUES rows, got {len(values)}"
    assert len(claims) == expected * 5, f"{name}: expected {expected * 5} CLAIM rows"
    return (int(fp.group(1)), float(fp.group(2)), float(fp.group(3))), values, claims


def spread(a: float, b: float) -> float:
    return abs(a - b) / max(abs(a), abs(b))


runs = {tag: parse(name) for tag, name in RUNS.items()}

print("=" * 72)
print("POST-4 step 1 — centerline rank dependence, attribution")
print("=" * 72)

print("\n1. mesh identity across rank counts (10 significant digits)")
fps = {tag: r[0] for tag, r in runs.items()}
ref = fps["n1"]
mesh_same = True
for tag, (cells, m1, m2) in fps.items():
    ok = cells == ref[0] and abs(m1 - ref[1]) <= 1e-10 * abs(ref[1]) and abs(m2 - ref[2]) <= 1e-10 * abs(ref[2])
    mesh_same &= ok
    print(f"  {tag}: cells={cells} m1={m1:.12e} m2={m2:.12e}  {'same' if ok else 'DIFFERENT'}")
print(f"  MESH_IDENTICAL = {mesh_same}")

print("\n2. ownership census — the suspect mechanism's necessary condition")
multi_rank = multi_cell = invalid = disagree = total = 0
for tag, (_fp, _v, claims) in runs.items():
    for c in claims:
        total += 1
        multi_rank += c["nranks"] > 1
        multi_cell += c["ncells"] > 1
        invalid += not c["valid"]
        disagree += c["maxcross"] > 0.0
print(f"  rows (point x field x set x rank count): {total}")
print(f"  MULTI_RANK_CLAIMS   = {multi_rank}/{total}")
print(f"  MULTI_CELL_CLAIMS   = {multi_cell}/{total}   (links[0] can only bite here)")
print(f"  MASK_INVALID        = {invalid}/{total}   (silent zero-fill candidate)")
print(f"  CROSS_CELL_DISAGREE = {disagree}/{total}")
ownership_possible = multi_cell > 0 or multi_rank > 0 or invalid > 0

print("\n3. rank spread per field and point set (max over the three rank pairs)")
pairs = [("n1", "n2"), ("n1", "n4"), ("n2", "n4")]
worst = {}
for s in SETS:
    for f in FIELDS:
        w = 0.0
        for a, b in pairs:
            va, vb = runs[a][1][(s, f)], runs[b][1][(s, f)]
            w = max(w, max(spread(x, y) for x, y in zip(va, vb)))
        worst[(s, f)] = w
        print(f"  {s:5s} {f:5s} max rank spread = {w * 100:10.6f}%")

print("\n   per-point detail, axis set, -n 2 vs -n 4 (EX-16's pair)")
for f in FIELDS:
    v2, v4 = runs["n2"][1][("axis", f)], runs["n4"][1][("axis", f)]
    row = "  ".join(f"{spread(a, b) * 100:8.4f}%" for a, b in zip(v2, v4))
    print(f"  {f:5s} {row}")

print("\n4. the epsilon-nudge discriminator (x = y = 1e-6 m)")
for f in FIELDS:
    print(
        f"  {f:5s} axis {worst[('axis', f)] * 100:10.6f}%  ->  "
        f"nudge {worst[('nudge', f)] * 100:10.6f}%  "
        f"({worst[('axis', f)] / max(worst[('nudge', f)], 1e-300):.4g}x)"
    )

lag = max(worst[("axis", "E_lag")], worst[("axis", "B_lag")])
src = max(worst[("axis", "E_src")], worst[("axis", "B_src")])
sep = lag / max(src, 1e-300)

print("\n" + "=" * 72)
print("ATTRIBUTION")
print("=" * 72)
print(f"  interpolant path (E_lag/B_lag) max rank spread : {lag * 100:.4f}%")
print(f"  source path      (E_src/B_src) max rank spread : {src * 100:.6f}%")
print(f"  separation, same points, same solves           : {sep:.4g}x")
print(f"  EX-16 centerline record (cited)                : {EX16_CENTERLINE * 100:.4f}%")
print(f"  EX-16 phantom-path control (cited)             : {EX16_PHANTOM * 100:.6f}%")
print(f"  ownership mechanism possible on this fixture   : {ownership_possible}")

ok = mesh_same and not ownership_possible and sep >= SEPARATION_MIN
print(
    f"\nANCHOR (mesh identical, zero multi-claims/mask holes, and the interpolant "
    f"path spreads >= {SEPARATION_MIN:.0f}x the source path): {'PASS' if ok else 'FAIL'}"
)
print(
    "VERDICT: the links[0] + last-writer-wins ownership tie-break is REFUTED on "
    "this fixture; the rank dependence enters at the interpolation into Lagrange "
    "P1, upstream of evaluate_vector_field_parallel."
    if ok
    else "VERDICT: anchor did not hold — read the census above before concluding."
)
sys.exit(0 if ok else 1)
