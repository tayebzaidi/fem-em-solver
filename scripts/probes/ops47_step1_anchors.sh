#!/usr/bin/env bash
# OPS-47 step 1 anchors — run inside the container through the harness:
#
#   scripts/testing/run_and_log.sh OPS-47-step1 "docker compose exec -T \
#     fem-em-solver bash -lc 'cd /workspace && timeout -k 30 30 \
#     bash scripts/probes/ops47_step1_anchors.sh'"
#
# (a) leak-check positive control under docs/planning/chunks/, then clean;
# (b) `chunks --narratives` self-test on a COPY of PROJECT_PLAN.md (POST-6);
# negative control (asserted): one altered chunk-file byte => refusal, copy unchanged;
# rider: the scripted size assert passes on a true bound and fails (exit 3) on a false one;
# (c) --dry-run over WF-6, TH-15, PORT-14, POST-6 reconciled line-for-line with
#     measure_plan_sections.py --blocks.
#
# Nothing here writes the real plan, the real chunk files or the real git index
# (method and the safe.directory trap: scripts/probes/ops46_step1_anchors.sh).
# The planted value is generated at run time, so it is never already "published"
# in a tracked file (the OPS-46 plant now is, which would subtract it in hook mode).
set -u
cd /workspace
W=logs/ops47-step1
TOOL=scripts/maintenance/rotate_plan_archive.py
LEAK=scripts/testing/check_private_leak.py
PLANT_SECRET_DIR=examples/ansys_benchmarks/zz_ops47_positive_control/aed_results
PLANT=docs/planning/chunks/_ops47_positive_control.md
SAFE=(GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=/workspace)
IDS=WF-6,TH-15,PORT-14,POST-6
PART=${1:-all}   # moves = (b), negative controls, rider, (c); leak = (a); all = both
fail=0

check() { # name rc expected
  if [ "$2" = "$3" ]; then echo "[anchor] $1: PASS (rc=$2, expected $3)"
  else echo "[anchor] $1: FAIL (rc=$2, expected $3)"; fail=1; fi
}
cleanup() {
  rm -f "$PLANT"
  rm -rf examples/ansys_benchmarks/zz_ops47_positive_control
}
trap cleanup EXIT

rm -rf "$W"; mkdir -p "$W/chunks"
sha256sum PROJECT_PLAN.md docs/planning/chunks/POST-6.md | tee "$W/real.sha256"
pointer() { printf '**`%s` narrative** — moved byte for byte to `docs/planning/chunks/%s.md` (`OPS-47`).' "$1" "$1"; }
: > "$W/spec-four.md"
for id in WF-6 TH-15 PORT-14 POST-6; do printf '=== %s\n%s\n' "$id" "$(pointer "$id")" >> "$W/spec-four.md"; done
printf '=== POST-6\n%s\n' "$(pointer POST-6)" > "$W/spec-post6.md"

if [ "$PART" != leak ]; then
echo "== (b) self-test on a copy: move POST-6's narrative"
cp PROJECT_PLAN.md "$W/plan.md"; cp PROJECT_PLAN.md "$W/plan.pre.md"
cp docs/planning/chunks/POST-6.md "$W/chunks/POST-6.md"; cp "$W/chunks/POST-6.md" "$W/POST-6.history.pre.md"
python3 "$TOOL" chunks "$W/spec-post6.md" --narratives --plan "$W/plan.md" --chunks-dir "$W/chunks" \
  --assert-below-bytes "$(stat -c %s "$W/plan.pre.md")"
check b-tool-exit-and-size-assert "$?" 0
python3 - "$W" <<'EOF'
import re, sys
w = sys.argv[1]
pre = open(f"{w}/plan.pre.md", "rb").read().decode("utf-8").split("\n")
# Independent re-extraction (not the tool's scanner): the one '**`POST-6`' opener
# inside §7, to the line before the next '**`<ID>`' opener / '| `<ID>`' row / heading.
s7 = next(i for i, l in enumerate(pre) if l.startswith("## 7."))
e7 = next(i for i in range(s7 + 1, len(pre)) if pre[i].startswith("## "))
opens = [i for i in range(s7, e7) if pre[i].startswith("**`POST-6`")]
assert len(opens) == 1, opens
a = opens[0]
b = next(i for i in range(a + 1, e7) if re.match(r"^(\*\*`[A-Z]+-\d+`|\| `[A-Z]+-\d+`|#{2,3} )", pre[i])) - 1
while not pre[b].strip():
    b -= 1
span = "\n".join(pre[a:b + 1]).encode("utf-8")
open(f"{w}/span.extracted", "wb").write(span)
hist = open(f"{w}/POST-6.history.pre.md", "rb").read()
new = open(f"{w}/chunks/POST-6.md", "rb").read()
assert new.startswith(hist), "row history not preserved"
hdr = "## Narrative — moved verbatim from PROJECT_PLAN.md §7 (OPS-47)\n\n".encode("utf-8")
tail = new[len(hist):]
k = tail.index(hdr)
body = tail[k + len(hdr):]
assert body.endswith(b"\n")
open(f"{w}/span.chunkfile", "wb").write(body[:-1])
ptr = [l for l in open(f"{w}/plan.md", encoding="utf-8").read().split("\n") if l.startswith("**`POST-6` narrative**")]
assert len(ptr) == 1, ptr
open(f"{w}/pointer.line", "wb").write(ptr[0].encode("utf-8"))
print(f"independent re-extraction: lines {a + 1}-{b + 1} ({b - a + 1} lines), {len(span)} B; "
      f"history {len(hist)} B preserved, appended tail {len(tail)} B")
print("pointer:", ptr[0])
EOF
check b-reextract-and-history-preserved "$?" 0
cmp "$W/span.extracted" "$W/span.chunkfile"; check b-cmp-chunkfile-span-vs-extracted "$?" 0
ext=$(stat -c %s "$W/span.extracted"); ptr=$(stat -c %s "$W/pointer.line")
before=$(stat -c %s "$W/plan.pre.md"); after=$(stat -c %s "$W/plan.md")
echo "span $ext B, pointer $ptr B; copy $before -> $after B (shrink $((before - after)) B, span - pointer $((ext - ptr)) B)"
[ $((before - after)) = $((ext - ptr)) ]; check b-shrink-equals-span-minus-pointer "$?" 0
[ -z "$(env "${SAFE[@]}" git diff --stat -- PROJECT_PLAN.md)" ]; check b-git-diff-stat-plan-empty "$?" 0
env "${SAFE[@]}" git diff --stat -- PROJECT_PLAN.md

echo "== negative control (asserted): one byte altered in the extracted chunk file"
cp "$W/plan.pre.md" "$W/plan.neg.md"; cp "$W/plan.neg.md" "$W/plan.neg.pre.md"
python3 -c "
p='$W/chunks/POST-6.md'; b=bytearray(open(p,'rb').read())
i=len(b)-400
b[i] = ord('X') if b[i] != ord('X') else ord('Y'); open(p,'wb').write(bytes(b)); print('altered byte', i, 'of', len(b))"
python3 "$TOOL" chunks "$W/spec-post6.md" --narratives --plan "$W/plan.neg.md" --chunks-dir "$W/chunks"
check neg-refuses "$?" 1
cmp "$W/plan.neg.md" "$W/plan.neg.pre.md"; check neg-plan-copy-unchanged "$?" 0

echo "== negative control 2 (asserted): a spec naming a chunk with no narrative"
printf '=== OPS-999\n%s\n' "$(pointer OPS-999)" > "$W/spec-missing.md"
python3 "$TOOL" chunks "$W/spec-missing.md" --narratives --plan "$W/plan.neg.md" --chunks-dir "$W/chunks"
check neg2-refuses-no-block "$?" 1
cmp "$W/plan.neg.md" "$W/plan.neg.pre.md"; check neg2-plan-copy-unchanged "$?" 0

echo "== rider: scripted size assert"
cp "$W/plan.pre.md" "$W/plan.size.md"; cp docs/planning/chunks/POST-6.md "$W/chunks-size-POST-6.md"
mkdir -p "$W/chunks-size"; cp docs/planning/chunks/POST-6.md "$W/chunks-size/POST-6.md"
python3 "$TOOL" chunks "$W/spec-post6.md" --narratives --dry-run --plan "$W/plan.size.md" \
  --chunks-dir "$W/chunks-size" --assert-below-bytes 1
check rider-false-bound-fails-exit3 "$?" 3
cmp "$W/plan.size.md" "$W/plan.pre.md"; check rider-dry-run-writes-nothing "$?" 0

echo "== (c) --dry-run over the four narratives on the REAL plan (writes nothing)"
python3 "$TOOL" chunks "$W/spec-four.md" --narratives --dry-run > "$W/dry.out"; rc=$?
cat "$W/dry.out"
check c-dry-run-exit "$rc" 0
python3 scripts/probes/measure_plan_sections.py PROJECT_PLAN.md --blocks "$IDS" > "$W/blocks.out"
check c-measure-exit "$?" 0
cat "$W/blocks.out"
python3 - "$W" <<'EOF'
import re, sys
w = sys.argv[1]
plan = open("PROJECT_PLAN.md", encoding="utf-8").read().split("\n")
dry = {m[0]: (int(m[1]), int(m[2]), int(m[3])) for m in
       re.findall(r"^(\S+)\s+narrative lines (\d+)-(\d+) \((\d+) lines\)", open(f"{w}/dry.out").read(), re.M)}
meas, cur = {}, None
for l in open(f"{w}/blocks.out").read().split("\n"):
    m = re.match(r"^== (\S+) status", l)
    if m:
        cur = m.group(1)
    m = re.match(r"^\s+nar (\d+)-(\d+) \((\d+) lines\)", l)
    if m and cur:
        meas.setdefault(cur, []).append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
bad = 0
for cid in ["WF-6", "TH-15", "PORT-14", "POST-6"]:
    a, b, n = dry[cid]
    blocks = [x for x in meas.get(cid, []) if x[0] <= a and b <= x[1]]
    if len(blocks) != 1 or n != b - a + 1:
        print(f"[reconcile] {cid}: FAIL no single measured nar block contains {a}-{b}: {meas.get(cid)}")
        bad = 1
        continue
    A, B, N = blocks[0]
    lead, trail = plan[A - 1:a - 1], plan[b:B]
    trail_blank = all(not l.strip() for l in trail)
    lead_named = [l[:70] for l in lead if re.match(r"^(?:[-*] )?\*\*`?" + re.escape(cid) + r"`?", l)]
    ok = trail_blank and not lead_named and len(lead) + n + len(trail) == N
    lead_ids = sorted(set(re.findall(r"\*\*`([A-Z]+-\d+)`\*\*", "\n".join(lead))))
    print(f"[reconcile] {cid}: {'PASS' if ok else 'FAIL'} measured nar {A}-{B} ({N}) = "
          f"{len(lead)} leading lines before the opener + tool {a}-{b} ({n}) + {len(trail)} trailing blank; "
          f"literal count match: {'yes' if n == N else 'no'}"
          + (f"; leading lines open {lead_ids}, first: {lead[0][:60]!r}" if lead else ""))
    bad = bad or (0 if ok else 1)
print(f"four-narrative total: tool {sum(v[2] for v in dry.values())} lines; "
      f"measured nar {sum(x[2] for c in dry for x in meas.get(c, []) if x[0] <= dry[c][0] and dry[c][1] <= x[1])} lines")
sys.exit(bad)
EOF
check c-reconcile-tool-vs-measure "$?" 0
python3 "$TOOL" chunks --census --narratives --min-lines 100 > "$W/census.out"
check c-census-exit "$?" 0
cat "$W/census.out"
sha256sum -c "$W/real.sha256"; check c-real-plan-and-chunk-file-unchanged "$?" 0

fi

if [ "$PART" != moves ]; then
echo "== (a) leak-check positive control under docs/planning/chunks/"
val="7.$(date +%N)$(date +%s | rev | cut -c1-4)"
mkdir -p "$PLANT_SECRET_DIR" "$W/objects"
echo "synthetic plant, not an AED figure: $val" > "$PLANT_SECRET_DIR/plant.txt"
echo "planted synthetic value $val (OPS-47 step 1 positive control)" > "$PLANT"
cp .git/index "$W/index"
export GIT_INDEX_FILE=/workspace/$W/index GIT_OBJECT_DIRECTORY=/workspace/$W/objects \
       GIT_ALTERNATE_OBJECT_DIRECTORIES=/workspace/.git/objects
env "${SAFE[@]}" git add "$PLANT"; check a-stage-plant-in-scratch-index "$?" 0
echo "staged in scratch index:"; env "${SAFE[@]}" git diff --cached --name-only
env "${SAFE[@]}" python3 "$LEAK" > "$W/leak-pos.out"; rc=$?
cat "$W/leak-pos.out"
check a-positive-control-caught "$rc" 1
grep -q "$PLANT" "$W/leak-pos.out"; check a-names-the-plant-file "$?" 0
unset GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES
cleanup
[ ! -e "$PLANT" ] && [ ! -e examples/ansys_benchmarks/zz_ops47_positive_control ]
check a-plant-removed "$?" 0
env "${SAFE[@]}" python3 "$LEAK"; check a-hook-mode-clean-tree "$?" 0
env "${SAFE[@]}" python3 "$LEAK" --audit; check a-audit-clean-tree "$?" 0
echo "real index staged paths: $(env "${SAFE[@]}" git diff --cached --name-only | wc -l)"
fi

echo "== summary: fail=$fail"
exit $fail
