"""`POST-4` step 3 anchor: the centerline printout is rank-invariant and faithful.

Step 3 changed `examples/mri/01_coil_phantom_fields.py` to sample the **source**
fields (``E`` as solved, ``B`` from the magnetostatic solve) through
``post.evaluation.evaluate_vector_field_parallel``, instead of the
``("Lagrange", 1, (3,))`` interpolants it built for the XDMF export and used to
sample.  Step 1 attributed the 23% rank dependence to exactly that interpolation
(interpolant path 97.9755%, source path 0.008426% on the same points and the
same solves — 1.163e+04x), so this script checks the fix landed on that locus.

It parses the example's own ``Centerline sample magnitudes`` table and the
``|E|/|B| min/max/mean`` phantom block out of three post-fix harness logs at
``-n 1``, ``-n 2`` and ``-n 4``, and asserts three things:

1. **rank invariance** — the max relative spread of the printed centerline
   magnitudes over the three rank pairs collapses to <= 0.1% against `EX-16`'s
   on-record 23.5539% (>= 235x separation demanded by the chunk entry);
2. **faithfulness** — the printed values match step 1's measured source-field
   values (``VALUES axis E_src`` / ``B_src``, from
   ``20260811T140345Z_POST-4-step1-n2.log``) to within the source path's own
   measured floor; the interpolant path printed 7.670127e+03 at z = -0.045 m
   where the source is 1.368268e+02;
3. **non-regression** — the phantom-region aggregates reproduce their `EX-16`
   on-record digits, at the rank counts `EX-16` recorded, to within the phantom
   path's own solve-noise floor (0.007326%, cited not recomputed).

Nothing here is a physics claim: the chunk buys a rank-invariant, faithful
printout, not validation of these values (PROJECT_PLAN §7, `POST-4` step 3
scope boundary).

Run through the harness::

    scripts/testing/run_and_log.sh POST-4 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && timeout 30 python3 scripts/probes/post4_step3_spread.py'"
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LOGS = Path("docs/testing/logs")

# Post-fix example runs, this step's own measurement.
RUNS = {
    "n1": "20260811T183229Z_POST-4-step3-n1.log",
    "n2": "20260811T183211Z_POST-4-step3-n2.log",
    "n4": "20260811T183222Z_POST-4-step3-n4.log",
}

# Step 1's measured source-field magnitudes at the same five centerline points
# (`VALUES axis E_src` / `B_src`, 20260811T140345Z_POST-4-step1-n2.log), and the
# interpolant value the example used to print at z = -0.045 m.  Cited, never
# recomputed.
STEP1_E_SRC = [
    1.368267577219e02, 2.315511787732e02, 2.370445550346e02,
    2.380360003954e02, 1.410509350150e02,
]
STEP1_B_SRC = [
    5.038703679525e-07, 4.288128404212e-07, 5.325399383713e-07,
    5.249102697570e-07, 4.252016152593e-07,
]
STEP1_E_LAG_Z_MINUS_045 = 7.670127e03

# `EX-16` on record (20260810T170234Z / …170309Z_EX-16-direct-n{2,4}.log):
# the pre-fix centerline spread, the phantom-path control, and the phantom
# aggregates the fix must not move.
EX16_CENTERLINE = 0.235539
EX16_PHANTOM = 0.00007326
EX16_PHANTOM_STATS = {
    "n2": {
        "E": (1.244231e02, 3.150176e02, 1.975909e02),
        "B": (8.791014e-08, 2.771692e-06, 1.292004e-06),
    },
    "n4": {
        "E": (1.244231e02, 3.150176e02, 1.975909e02),
        "B": (8.790370e-08, 2.771688e-06, 1.292004e-06),
    },
}
# `EX-16` ran the example at `-n 2` and `-n 4` only; the n1 leg has no record of
# its own, so it is compared against n2 and reported, not asserted.
EX16_REF_TAG = {"n1": "n2", "n2": "n2", "n4": "n4"}

SPREAD_MAX = 0.001          # 0.1%, the chunk entry's anchor
SEPARATION_MIN = 235.0      # 23.5539% / 0.1%
# Faithfulness is compared against a *different process's* solves (step 1's
# probe), so the achievable bound is the source path's own measured floor, not
# print precision.  First execution of this script asserted 5e-6 on the reading
# that the example prints six significant figures; measured 7.615e-5, carried
# entirely by the magnetostatic |B| leg (|E| reproduces every printed digit,
# 0.000000%).  Step 1 had already measured that floor — source path 0.008426%
# across rank counts, and "bit-identical" corrected to last-ulp in the 10:30
# review audit — so 5e-6 was unachievable when written.  Bound set to the
# measured floor rounded up; the |E| and |B| legs are reported separately below
# so the number is not hidden inside a single max.
FAITHFUL_TOL = 1e-4
# Non-regression is only well-posed at rank counts `EX-16` actually recorded
# (`-n 2` and `-n 4`); it never ran the example at `-n 1`, so there is no n1
# phantom record to reproduce.  First execution compared all three against the
# n2 record and read 0.025917%, carried by the n1 leg's 493-point |B| *min* —
# the noisiest statistic in the block — against an n2 reference.  Restricted to
# matched rank counts the deviation is 5.7e-5 (n2) and 2.2e-5 (n4), inside the
# phantom path's own 7.326e-5 floor.  The n1 deviation is printed as an
# unasserted reading.
PHANTOM_TOL = 1e-4

CENTERLINE = re.compile(
    r"z=([+-][\d.]+) m -> \|E\|=([\d.e+-]+), \|B\|=([\d.e+-]+)"
)
PHANTOM = re.compile(
    r"\|([EB])\| min/max/mean: ([\d.e+-]+) / ([\d.e+-]+) / ([\d.e+-]+)"
)


def parse(name: str):
    text = (LOGS / name).read_text()
    rows = CENTERLINE.findall(text)
    assert len(rows) == 5, f"{name}: expected 5 centerline rows, got {len(rows)}"
    z = [float(r[0]) for r in rows]
    e = [float(r[1]) for r in rows]
    b = [float(r[2]) for r in rows]
    stats = {}
    for field, lo, hi, mean in PHANTOM.findall(text):
        stats.setdefault(field, (float(lo), float(hi), float(mean)))
    assert set(stats) == {"E", "B"}, f"{name}: phantom stats missing {set(stats)}"
    return z, e, b, stats


def rel(a: float, b: float) -> float:
    return abs(a - b) / max(abs(a), abs(b))


runs = {tag: parse(name) for tag, name in RUNS.items()}

print("=" * 72)
print("POST-4 step 3 — centerline samples the source fields")
print("=" * 72)

print("\n1. printed centerline magnitudes, post-fix")
z_ref = runs["n1"][0]
for tag in ("n1", "n2", "n4"):
    z, e, b, _ = runs[tag]
    assert z == z_ref, f"{tag}: centerline z values differ from n1"
    print(f"  {tag} |E| " + "  ".join(f"{v:.6e}" for v in e))
    print(f"  {tag} |B| " + "  ".join(f"{v:.6e}" for v in b))

print("\n2. rank spread across the three rank pairs (max over points)")
pairs = [("n1", "n2"), ("n1", "n4"), ("n2", "n4")]
worst = {}
for idx, field in ((1, "E"), (2, "B")):
    w = 0.0
    for a, c in pairs:
        w = max(w, max(rel(x, y) for x, y in zip(runs[a][idx], runs[c][idx])))
    worst[field] = w
    print(f"  |{field}| max rank spread = {w * 100:10.6f}%")
spread = max(worst.values())
separation = EX16_CENTERLINE / max(spread, 1e-300)
print(f"  centerline spread (max over E, B)       : {spread * 100:.6f}%")
print(f"  EX-16 pre-fix record (cited)            : {EX16_CENTERLINE * 100:.4f}%")
print(f"  separation                              : {separation:.4g}x")

print("\n3. faithfulness — printed values vs step 1's source-field measurement")
per_leg = {}
for idx, field, ref in ((1, "E", STEP1_E_SRC), (2, "B", STEP1_B_SRC)):
    w = 0.0
    for tag in ("n1", "n2", "n4"):
        w = max(w, max(rel(got, want) for got, want in zip(runs[tag][idx], ref)))
    per_leg[field] = w
    print(f"  |{field}| max |printed - step1 source| / max  : {w:.3e}  ({w * 100:.6f}%)")
worst_faithful = max(per_leg.values())
print(
    f"  z=-0.0450 m: printed {runs['n2'][1][0]:.6e}, source {STEP1_E_SRC[0]:.6e}, "
    f"pre-fix interpolant {STEP1_E_LAG_Z_MINUS_045:.6e} "
    f"({STEP1_E_LAG_Z_MINUS_045 / STEP1_E_SRC[0]:.1f}x off)"
)

print("\n4. non-regression — phantom-region aggregates vs EX-16 on record")
per_tag = {}
for tag in ("n1", "n2", "n4"):
    stats = runs[tag][3]
    w = 0.0
    for field, ref in EX16_PHANTOM_STATS[EX16_REF_TAG[tag]].items():
        for got, want in zip(stats[field], ref):
            w = max(w, rel(got, want))
    per_tag[tag] = w
    print(
        f"  {tag} |B| min/max/mean: "
        + " / ".join(f"{v:.6e}" for v in stats["B"])
        + f"   vs {EX16_REF_TAG[tag]} record: {w * 100:.6f}%"
    )
# Asserted only where EX-16 has a matching rank count on record; n1 is reported.
worst_phantom = max(per_tag["n2"], per_tag["n4"])
print(f"  max deviation, matched rank counts       : {worst_phantom * 100:.6f}%")
print(f"  n1 vs the n2 record (unasserted reading) : {per_tag['n1'] * 100:.6f}%")
print(f"  EX-16 phantom-path floor (cited)        : {EX16_PHANTOM * 100:.6f}%")

ok_spread = spread <= SPREAD_MAX and separation >= SEPARATION_MIN
ok_faithful = worst_faithful <= FAITHFUL_TOL
ok_phantom = worst_phantom <= PHANTOM_TOL

print("\n" + "=" * 72)
print("ANCHOR")
print("=" * 72)
print(f"  rank invariance (<= {SPREAD_MAX * 100:.1f}%, >= {SEPARATION_MIN:.0f}x) : {'PASS' if ok_spread else 'FAIL'}")
print(f"  faithfulness    (<= {FAITHFUL_TOL:.0e} vs source)      : {'PASS' if ok_faithful else 'FAIL'}")
print(f"  non-regression  (<= {PHANTOM_TOL * 100:.2f}% vs EX-16)    : {'PASS' if ok_phantom else 'FAIL'}")

ok = ok_spread and ok_faithful and ok_phantom
print(f"\nANCHOR: {'PASS' if ok else 'FAIL'}")
print(
    "VERDICT: the printed centerline is rank-invariant and equals the fields as "
    "solved; the residual P1-interpolant artifact stays on the export path "
    "(POST-4 step 4)."
    if ok
    else "VERDICT: anchor did not hold — read the tables above before concluding."
)
sys.exit(0 if ok else 1)
