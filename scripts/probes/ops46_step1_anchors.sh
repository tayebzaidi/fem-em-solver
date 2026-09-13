#!/usr/bin/env bash
# OPS-46 step 1 anchors — run inside the container through the harness:
#
#   scripts/testing/run_and_log.sh OPS-46-step1 "docker compose exec -T \
#     fem-em-solver bash -lc 'cd /workspace && timeout -k 10 120 \
#     bash scripts/probes/ops46_step1_anchors.sh'"
#
# (a) leak-check positive control under docs/planning/chunks/, then clean;
# (b) `chunks` self-test on a COPY of PROJECT_PLAN.md (OPS-36);
# negative controls: one altered chunk-file byte, and a row that does not exist;
# (c) census dry run over every §7 row > 2 048 B, compared with the §9 lists.
#
# Nothing here writes the real plan or the real git index. The leak control
# stages its plant into a throwaway index and object directory under logs/
# (GIT_INDEX_FILE / GIT_OBJECT_DIRECTORY), so the container's root uid never
# writes into .git. The container's git refuses /workspace as "dubious
# ownership" unless safe.directory is set, and check_private_leak.py swallows
# git errors into "nothing staged" — so without the override below the
# positive control passes vacuously. That case is printed, not asserted.
set -u
cd /workspace
W=logs/ops46-step1
TOOL=scripts/maintenance/rotate_plan_archive.py
LEAK=scripts/testing/check_private_leak.py
PLANT_SECRET_DIR=examples/ansys_benchmarks/zz_ops46_positive_control/aed_results
PLANT=docs/planning/chunks/_ops46_positive_control.md
SAFE=(GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=/workspace)
fail=0

check() { # name rc expected
  if [ "$2" = "$3" ]; then echo "[anchor] $1: PASS (rc=$2, expected $3)"
  else echo "[anchor] $1: FAIL (rc=$2, expected $3)"; fail=1; fi
}
cleanup() {
  rm -f "$PLANT"
  rmdir docs/planning/chunks 2>/dev/null
  rm -rf examples/ansys_benchmarks/zz_ops46_positive_control
}
trap cleanup EXIT

rm -rf "$W"; mkdir -p "$W"
pre_chunks_dir=absent; [ -d docs/planning/chunks ] && pre_chunks_dir=present
echo "docs/planning/chunks before: $pre_chunks_dir"

echo "== (b) self-test on a copy: move OPS-36"
cp PROJECT_PLAN.md "$W/plan.md"; cp PROJECT_PLAN.md "$W/plan.pre.md"
printf '=== OPS-36\n%s\n' "Closed; the retention policy, the harness chatter filter and the weekly housekeeping sweep are in place." > "$W/spec-ops36.md"
python3 "$TOOL" chunks "$W/spec-ops36.md" --plan "$W/plan.md" --chunks-dir "$W/chunks"
check b-tool-exit "$?" 0
python3 - "$W" <<'EOF'
import sys
w = sys.argv[1]
def row(p):
    r = [l for l in open(p, encoding="utf-8").read().split("\n") if l.startswith("| `OPS-36` |")]
    assert len(r) == 1, len(r)
    return r[0].encode("utf-8")
o, n = row(f"{w}/plan.pre.md"), row(f"{w}/plan.md")
pre, suf = b"| `OPS-36` |", b"| smoke |"
assert o.startswith(pre) and o.endswith(suf) and n.startswith(pre) and n.endswith(suf)
open(f"{w}/cell.extracted", "wb").write(o[len(pre):-len(suf)])
open(f"{w}/cell.replacement", "wb").write(n[len(pre):-len(suf)])
body = open(f"{w}/chunks/OPS-36.md", "rb").read().split(b"\n\n", 1)[1]
assert body.endswith(b"\n")
open(f"{w}/cell.chunkbody", "wb").write(body[:-1])
print(f"independent re-extraction: old row {len(o)} B, new row {len(n)} B")
print("new row:", n.decode("utf-8"))
EOF
check b-reextract "$?" 0
cmp "$W/cell.extracted" "$W/cell.chunkbody"; check b-cmp-chunkbody-vs-cell "$?" 0
ext=$(stat -c %s "$W/cell.extracted"); body=$(stat -c %s "$W/cell.chunkbody")
rep=$(stat -c %s "$W/cell.replacement")
before=$(stat -c %s "$W/plan.pre.md"); after=$(stat -c %s "$W/plan.md")
echo "cell $ext B, chunk body $body B, replacement $rep B; copy $before -> $after B"
[ "$ext" = "$body" ]; check b-byte-count-equal "$?" 0
[ $((before - after)) = $((ext - rep)) ]; check b-shrink-equals-cell-minus-replacement "$?" 0
[ -z "$(env "${SAFE[@]}" git diff --stat -- PROJECT_PLAN.md)" ]; check b-real-plan-untouched "$?" 0
env "${SAFE[@]}" git diff --stat -- PROJECT_PLAN.md

echo "== negative control 1 (asserted): one byte altered after extraction"
cp "$W/plan.pre.md" "$W/plan.md"; cp "$W/plan.md" "$W/plan.neg1.pre.md"
python3 -c "
p='$W/chunks/OPS-36.md'; b=bytearray(open(p,'rb').read()); i=len(b)//2
b[i] = ord('X') if b[i] != ord('X') else ord('Y'); open(p,'wb').write(bytes(b)); print('altered byte', i)"
python3 "$TOOL" chunks "$W/spec-ops36.md" --plan "$W/plan.md" --chunks-dir "$W/chunks"
check neg1-refuses "$?" 1
cmp "$W/plan.md" "$W/plan.neg1.pre.md"; check neg1-plan-copy-unchanged "$?" 0

echo "== negative control 2 (asserted): spec names a row that does not exist"
printf '=== OPS-999\n%s\n' "No such row." > "$W/spec-missing.md"
python3 "$TOOL" chunks "$W/spec-missing.md" --plan "$W/plan.md" --chunks-dir "$W/chunks-missing"
check neg2-refuses "$?" 1
cmp "$W/plan.md" "$W/plan.neg1.pre.md"; check neg2-plan-copy-unchanged "$?" 0
[ ! -e "$W/chunks-missing" ]; check neg2-nothing-written "$?" 0

echo "== (c) census dry run over PROJECT_PLAN.md (writes nothing)"
cp PROJECT_PLAN.md "$W/plan.census.pre.md"
python3 "$TOOL" chunks --census --plan PROJECT_PLAN.md > "$W/census.out"; rc=$?
cat "$W/census.out"
check c-census-all-parse "$rc" 0
cmp PROJECT_PLAN.md "$W/plan.census.pre.md"; check c-plan-unchanged "$?" 0
python3 - "$W/census.out" <<'EOF'
import re, sys
# The 73 IDs §9 items 3-5 name (2026-09-12 18:00 review).
listed = ("WF-6 ANS-1 ANS-2 ANS-4 PORT-9 PORT-11 PORT-12 PORT-13 PORT-15 PORT-16 PORT-18 PORT-19 "
          "OPS-17 OPS-18 OPS-26 OPS-27 " + " ".join(f"OPS-{i}" for i in range(30, 35)) + " "
          + " ".join(f"OPS-{i}" for i in range(36, 47)) + " GEO-19 GEO-20 "
          + " ".join(f"GEO-{i}" for i in range(23, 33)) + " MAG-18 MAG-19 TH-11 TH-12 TH-15 TH-19 "
          "MAT-6 MAT-8 POST-5 POST-6 " + " ".join(f"EX-{i}" for i in range(24, 29)) + " EX-30 EX-36 "
          + " ".join(f"EX-{i}" for i in range(42, 54))).split()
text = open(sys.argv[1], encoding="utf-8").read()
found = re.findall(r"^([A-Z]+-\d+)\s", text, re.M)
print(f"§9 lists {len(listed)} IDs ({len(set(listed))} distinct); census finds {len(found)}")
print("in census, not in §9 lists:", sorted(set(found) - set(listed)))
print("in §9 lists, not in census:", sorted(set(listed) - set(found)))
EOF

echo "== (a) leak-check positive control under docs/planning/chunks/"
mkdir -p "$PLANT_SECRET_DIR" docs/planning/chunks "$W/objects"
echo "synthetic plant, not an AED figure: 7.304928167351" > "$PLANT_SECRET_DIR/plant.txt"
echo "planted synthetic value 7.304928167351 (OPS-46 step 1 positive control)" > "$PLANT"
cp .git/index "$W/index"
export GIT_INDEX_FILE=/workspace/$W/index GIT_OBJECT_DIRECTORY=/workspace/$W/objects \
       GIT_ALTERNATE_OBJECT_DIRECTORIES=/workspace/.git/objects
env "${SAFE[@]}" git add "$PLANT"; check a-stage-plant-in-scratch-index "$?" 0
echo "staged in scratch index:"; env "${SAFE[@]}" git diff --cached --name-only
env "${SAFE[@]}" python3 "$LEAK" > "$W/leak-pos.out"; rc=$?
cat "$W/leak-pos.out"
check a-positive-control-caught "$rc" 1
grep -q "$PLANT" "$W/leak-pos.out"; check a-names-the-plant-file "$?" 0
python3 "$LEAK" > "$W/leak-nosafe.out"; rc=$?
echo "[printed, not asserted] same plant WITHOUT safe.directory: rc=$rc (predicted 0 — git refuses, the check sees nothing staged)"
unset GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES
cleanup
[ ! -e "$PLANT" ] && [ ! -e examples/ansys_benchmarks/zz_ops46_positive_control ]
check a-plant-removed "$?" 0
env "${SAFE[@]}" python3 "$LEAK"; check a-hook-mode-clean-tree "$?" 0
env "${SAFE[@]}" python3 "$LEAK" --audit; check a-audit-clean-tree "$?" 0
env "${SAFE[@]}" git diff --cached --name-only | grep -c . ; echo "(real index: staged path count above)"

echo "== summary: fail=$fail"
exit $fail
