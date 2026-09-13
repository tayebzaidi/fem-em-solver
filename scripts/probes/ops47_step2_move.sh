#!/usr/bin/env bash
# OPS-47 step 2 — move one §7 narrative per run, with the step-2 anchors.
# Run inside the container through the harness, one mode per window:
#
#   scripts/testing/run_and_log.sh OPS-47-step2-<MODE> "docker compose exec -T \
#     fem-em-solver bash -lc 'cd /workspace && timeout -k 30 30 \
#     bash scripts/probes/ops47_step2_move.sh <neg|move ID|final>'"
#
# neg        negative control (asserted, once, before the first real move): the tool
#            refuses a spec naming a real chunk ID with no narrative section, plan and
#            chunks dir untouched; plus the stale-line-cite scan on the pre-move plan.
# move ID    (i) re-extract ID's span from `git show HEAD:PROJECT_PLAN.md` (the
#            pre-commit revision) with an independent scanner, cmp against the
#            chunk-file span, and cmp the whole written plan against HEAD with that
#            span replaced by the pointer; (ii) check_private_leak.py --audit rc 0;
#            (iii) plan lines/bytes before/after, measure_plan_sections.py §7 lines
#            before/after, and the tool's --assert-below-* rider with the pre-move
#            size as the strict bound. `move WF-6` also records the 4 000-line guide
#            as a projected --assert-below-lines 4000 reading (rc 3 = not met).
# final      (iv) every §N / §N.M in CLAUDE.md and docs/automation/*.md resolves to a
#            PROJECT_PLAN.md heading; census of remaining narratives >= 100 lines.
#
# Span definition (ratified for the slot, the step-1 tool's): from the chunk's opener
# line `**`ID` …` to the line before the next §7 table row, ##/### heading or another
# chunk's opener (same-ID openers continue), trailing blank lines dropped.
set -u
cd /workspace
TOOL=scripts/maintenance/rotate_plan_archive.py
LEAK=scripts/testing/check_private_leak.py
MEAS=scripts/probes/measure_plan_sections.py
SAFE=(GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=/workspace)
MODE=${1:?mode}
fail=0
check() { # name rc expected
  if [ "$2" = "$3" ]; then echo "[anchor] $1: PASS (rc=$2, expected $3)"
  else echo "[anchor] $1: FAIL (rc=$2, expected $3)"; fail=1; fi
}
pointer() { printf '**`%s` narrative** — moved byte for byte to `docs/planning/chunks/%s.md` (`OPS-47`).' "$1" "$1"; }
sizes() { python3 -c "
import sys; b=open(sys.argv[1],'rb').read(); print(len(b), b.decode('utf-8').count('\n')+1)" "$1"; }

case "$MODE" in
neg)
  W=logs/ops47-step2/neg; rm -rf "$W"; mkdir -p "$W"
  echo "HEAD $(env "${SAFE[@]}" git rev-parse HEAD)"
  sha256sum PROJECT_PLAN.md > "$W/plan.sha256"
  ls docs/planning/chunks > "$W/chunks.ls.pre"
  echo "== negative control: OPS-46 has a §7 row but no narrative section"
  grep -c '^| `OPS-46` |' PROJECT_PLAN.md
  printf '=== OPS-46\n%s\n' "$(pointer OPS-46)" > "$W/spec-neg.md"
  python3 "$TOOL" chunks "$W/spec-neg.md" --narratives > "$W/neg.out"; rc=$?
  cat "$W/neg.out"
  check neg-refuses-chunk-with-no-block "$rc" 1
  grep -q "REFUSED: OPS-46: 0 §7 narrative sections" "$W/neg.out"; check neg-refusal-names-zero-sections "$?" 0
  sha256sum -c "$W/plan.sha256"; check neg-real-plan-unchanged "$?" 0
  ls docs/planning/chunks > "$W/chunks.ls.post"
  cmp "$W/chunks.ls.pre" "$W/chunks.ls.post"; check neg-chunks-dir-listing-unchanged "$?" 0
  echo "== dry run over the four (re-measure; writes nothing)"
  : > "$W/spec-four.md"
  for id in POST-6 PORT-14 TH-15 WF-6; do printf '=== %s\n%s\n' "$id" "$(pointer "$id")" >> "$W/spec-four.md"; done
  python3 "$TOOL" chunks "$W/spec-four.md" --narratives --dry-run --assert-below-lines 4000; rc=$?
  echo "[guide] projected four-move plan --assert-below-lines 4000: rc=$rc (3 = guide not met; a reading, not an anchor)"
  sha256sum -c "$W/plan.sha256"; check dry-run-real-plan-unchanged "$?" 0
  echo "== stale line-cite scan (pre-move numbering): cites landing inside the four spans"
  python3 - <<'EOF'
import re, subprocess
plan = open("PROJECT_PLAN.md", encoding="utf-8").read().split("\n")
op = re.compile(r"^(?:[-*] )?\*\*`?([A-Z]+-[0-9]+)`?")
row = re.compile(r"^\| `([A-Z]+-[0-9]+)`")
s7 = next(i for i, l in enumerate(plan) if l.startswith("## 7."))
e7 = next(i for i in range(s7 + 1, len(plan)) if plan[i].startswith("## "))
spans = {}
for cid in ["POST-6", "PORT-14", "TH-15", "WF-6"]:
    a = [i for i in range(s7, e7) if (m := op.match(plan[i])) and m.group(1) == cid][0]
    b = next(i for i in range(a + 1, e7) if row.match(plan[i]) or plan[i].startswith(("## ", "### "))
             or ((m := op.match(plan[i])) and m.group(1) != cid)) - 1
    while not plan[b].strip():
        b -= 1
    spans[cid] = (a + 1, b + 1)
print("spans (1-indexed):", spans)
pat = re.compile(r"(?:PROJECT_PLAN(?:\.md)?[: ]\s*(?:lines? |L)?|plan lines? |§7 lines? |\blines? |\bL)(\d{3,5})(?:\s*[–-]\s*(\d{3,5}))?")
def inside(n):
    return [c for c, (a, b) in spans.items() if a <= n <= b]
for path in ["PROJECT_PLAN.md", "docs/testing/known-issues.md"]:
    txt = open(path, encoding="utf-8").read().split("\n")
    for k, l in enumerate(txt, 1):
        if path == "PROJECT_PLAN.md" and any(a <= k <= b for a, b in spans.values()):
            continue  # cites inside a moved span travel with it
        for m in pat.finditer(l):
            n = int(m.group(1)); hit = inside(n)
            if hit and ("PROJECT_PLAN" in l or "plan" in l.lower() or path == "PROJECT_PLAN.md"):
                print(f"[cite] {path}:{k}: '{m.group(0)}' -> inside {hit} :: {l.strip()[:110]}")
EOF
  ;;
move)
  ID=${2:?chunk id}
  W=logs/ops47-step2/$ID; rm -rf "$W"; mkdir -p "$W"
  HEAD=$(env "${SAFE[@]}" git rev-parse HEAD); echo "pre-commit revision HEAD $HEAD"
  env "${SAFE[@]}" git show HEAD:PROJECT_PLAN.md > "$W/plan.head.md"
  cmp PROJECT_PLAN.md "$W/plan.head.md"; check pre-worktree-plan-equals-HEAD "$?" 0
  if env "${SAFE[@]}" git cat-file -e "HEAD:docs/planning/chunks/$ID.md" 2>/dev/null; then
    env "${SAFE[@]}" git show "HEAD:docs/planning/chunks/$ID.md" > "$W/chunk.head.md"; echo "chunk file at HEAD: $(stat -c %s "$W/chunk.head.md") B"
  else
    printf '# %s\n' "$ID" > "$W/chunk.head.md"; echo "chunk file absent at HEAD (tool creates it with a '# $ID' title)"
    [ ! -e "docs/planning/chunks/$ID.md" ]; check pre-chunk-file-absent-on-disk "$?" 0
  fi
  read -r B0 L0 < <(sizes PROJECT_PLAN.md)
  echo "(iii) BEFORE: PROJECT_PLAN.md $L0 lines, $B0 B"
  python3 "$MEAS" PROJECT_PLAN.md 1 > "$W/measure.before"; check iii-measure-before-exit "$?" 0
  grep '^§7 lines' "$W/measure.before" | sed 's/^/(iii) BEFORE measure_plan_sections.py: /'
  printf '=== %s\n%s\n' "$ID" "$(pointer "$ID")" > "$W/spec.md"
  echo "== dry run"
  python3 "$TOOL" chunks "$W/spec.md" --narratives --dry-run --assert-below-lines "$L0" --assert-below-bytes "$B0"
  check dry-run-exit "$?" 0
  if [ "$ID" = WF-6 ]; then
    python3 "$TOOL" chunks "$W/spec.md" --narratives --dry-run --assert-below-lines 4000; rc=$?
    echo "[guide] projected post-WF-6 plan --assert-below-lines 4000: rc=$rc (3 = the 4 000-line guide is NOT met; a reading)"
  fi
  cmp PROJECT_PLAN.md "$W/plan.head.md"; check dry-run-wrote-nothing "$?" 0
  echo "== real move (rider: strict shrink asserted against the pre-move size)"
  python3 "$TOOL" chunks "$W/spec.md" --narratives --assert-below-lines "$L0" --assert-below-bytes "$B0"
  check move-exit-and-size-assert "$?" 0
  echo "== (i) independent re-extraction from git HEAD vs the chunk-file span"
  python3 - "$W" "$ID" <<'EOF'
import re, sys
w, cid = sys.argv[1], sys.argv[2]
head = open(f"{w}/plan.head.md", "rb").read().decode("utf-8").split("\n")
op = re.compile(r"^(?:[-*] )?\*\*`?([A-Z]+-[0-9]+)`?")
row = re.compile(r"^\| `([A-Z]+-[0-9]+)`")
s7 = next(i for i, l in enumerate(head) if l.startswith("## 7."))
e7 = next(i for i in range(s7 + 1, len(head)) if head[i].startswith("## "))
opens = [i for i in range(s7, e7) if (m := op.match(head[i])) and m.group(1) == cid]
a = opens[0]
b = next((i for i in range(a + 1, e7) if row.match(head[i]) or head[i].startswith(("## ", "### "))
          or ((m := op.match(head[i])) and m.group(1) != cid)), e7) - 1
while not head[b].strip():
    b -= 1
assert all(a <= i <= b for i in opens), f"{cid} opener outside the span: {opens}"
span = "\n".join(head[a:b + 1]).encode("utf-8")
open(f"{w}/span.git-head", "wb").write(span)
pre = open(f"{w}/chunk.head.md", "rb").read()
new = open(f"docs/planning/chunks/{cid}.md", "rb").read()
hdr = "\n## Narrative — moved verbatim from PROJECT_PLAN.md §7 (OPS-47)\n\n".encode("utf-8")
ok_prefix = new.startswith(pre)
tail = new[len(pre):]
if not pre.endswith(b"\n"):
    tail = tail[1:]
ok_hdr = tail.startswith(hdr) and new.count(hdr.strip()) == 1
body = tail[len(hdr):]
ok_nl = body.endswith(b"\n")
open(f"{w}/span.chunkfile", "wb").write(body[:-1] if ok_nl else body)
ptr = [l for l in open("PROJECT_PLAN.md", encoding="utf-8").read().split("\n")
       if l.startswith(f"**`{cid}` narrative**")]
exp = "\n".join(head[:a] + ptr[:1] + head[b + 1:]).encode("utf-8")
open(f"{w}/plan.expected", "wb").write(exp)
print(f"git-HEAD re-extraction: lines {a + 1}-{b + 1} ({b - a + 1} lines), {len(span)} B; "
      f"{len(opens)} same-ID opener line(s) inside; pointer lines in plan {len(ptr)}; "
      f"chunk file {len(pre)} -> {len(new)} B")
print(f"history prefix preserved: {ok_prefix}; single header: {ok_hdr}; trailing newline: {ok_nl}")
sys.exit(0 if (ok_prefix and ok_hdr and ok_nl and len(ptr) == 1) else 1)
EOF
  check i-reextract-prefix-header-pointer "$?" 0
  cmp "$W/span.git-head" "$W/span.chunkfile"; check i-cmp-git-HEAD-span-vs-chunkfile-span "$?" 0
  cmp "$W/plan.expected" PROJECT_PLAN.md; check i-cmp-plan-equals-HEAD-with-span-replaced-by-pointer "$?" 0
  read -r B1 L1 < <(sizes PROJECT_PLAN.md)
  SPAN=$(stat -c %s "$W/span.git-head"); PTR=$(pointer "$ID" | wc -c)
  echo "(iii) AFTER: PROJECT_PLAN.md $L1 lines, $B1 B (was $L0 lines, $B0 B; -$((L0 - L1)) lines, -$((B0 - B1)) B; span $SPAN B - pointer $PTR B = $((SPAN - PTR)) B)"
  [ $((B0 - B1)) = $((SPAN - PTR)) ]; check iii-shrink-equals-span-minus-pointer "$?" 0
  python3 "$MEAS" PROJECT_PLAN.md 1 > "$W/measure.after"; check iii-measure-after-exit "$?" 0
  grep '^§7 lines' "$W/measure.after" | sed 's/^/(iii) AFTER measure_plan_sections.py: /'
  echo "== (ii) leak audit"
  env "${SAFE[@]}" python3 "$LEAK" --audit; check ii-leak-audit "$?" 0
  env "${SAFE[@]}" git diff --stat
  ;;
final)
  echo "HEAD $(env "${SAFE[@]}" git rev-parse HEAD)"
  read -r B1 L1 < <(sizes PROJECT_PLAN.md)
  echo "PROJECT_PLAN.md final: $L1 lines, $B1 B"
  python3 "$MEAS" PROJECT_PLAN.md 5; check measure-exit "$?" 0
  python3 "$TOOL" chunks --census --narratives --min-lines 100; check census-exit "$?" 0
  echo "== (iv) § references in CLAUDE.md and docs/automation/*.md resolve to plan headings"
  python3 - <<'EOF'
import glob, re, sys
heads = [l for l in open("PROJECT_PLAN.md", encoding="utf-8").read().split("\n") if l.startswith(("## ", "### "))]
top = {m.group(1) for l in heads if (m := re.match(r"^## (\d+)\. ", l))}
sub = {m.group(1) for l in heads if (m := re.match(r"^### (\d+\.\d+) ", l))}
print("plan ## N:", sorted(top, key=int), " ### N.M:", sorted(sub))
bad = n = 0
seen = {}
for path in ["CLAUDE.md"] + sorted(glob.glob("docs/automation/*.md")):
    for k, l in enumerate(open(path, encoding="utf-8").read().split("\n"), 1):
        for m in re.finditer(r"§(\d+)(?:\.(\d+))?", l):
            ref = m.group(0)[1:]
            ok = (ref in sub) if m.group(2) else (ref in top)
            n += 1
            seen[ref] = seen.get(ref, 0) + 1
            if not ok:
                bad += 1
                print(f"[unresolved] {path}:{k}: §{ref} :: {l.strip()[:100]}")
print(f"§ references: {n} ({dict(sorted(seen.items()))}); unresolved {bad}")
sys.exit(1 if bad else 0)
EOF
  check iv-section-refs-resolve "$?" 0
  python3 -c "import sys; n=open('PROJECT_PLAN.md','rb').read().count(b'\n')+1; print(f'[guide] plan {n} lines < 4000: {\"MET\" if n < 4000 else \"NOT MET\"}')"
  ;;
*) echo "unknown mode $MODE"; exit 2 ;;
esac
echo "== summary: fail=$fail"
exit $fail
