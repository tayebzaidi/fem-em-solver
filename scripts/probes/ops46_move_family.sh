#!/usr/bin/env bash
# OPS-46 steps 2-4: move one §7 family's heavy rows to docs/planning/chunks/.
# Run inside the container through the harness, from a clean tree:
#
#   scripts/testing/run_and_log.sh OPS-46-step2-<FAM> "docker compose exec -T \
#     fem-em-solver bash -lc 'cd /workspace && timeout -k 10 120 \
#     bash scripts/probes/ops46_move_family.sh <FAM> <spec> [--negative-control]'"
#
# Anchors, per family: (i) every moved row's span re-extracted from
# `git show HEAD:PROJECT_PLAN.md` — independently of the tool's parser, using
# only the ID prefix and the unchanged trailing cells — equals the chunk-file
# body (`cmp`); (ii) check_private_leak.py exits 0 on the move staged into a
# throwaway index (safe.directory set, and git asserted to see the staged
# files, so the pass is not vacuous); (iii) `git diff --numstat` on the plan is
# exactly one changed line per moved row, and the only other change is the new
# chunk files. `--negative-control` first asserts the tool refuses a row that
# does not exist. New files are chowned to the host uid so later host-side
# edits are not blocked by root ownership.
set -u
cd /workspace
FAM=$1; SPEC=$2; NEG=${3:-}
TOOL=scripts/maintenance/rotate_plan_archive.py
W=logs/ops46-move-$FAM
HOST_UID=1000; HOST_GID=1000
SAFE=(GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=/workspace)
g() { env "${SAFE[@]}" git "$@"; }
fail=0
check() { # name rc expected
  if [ "$2" = "$3" ]; then echo "[anchor] $1: PASS (rc=$2, expected $3)"
  else echo "[anchor] $1: FAIL (rc=$2, expected $3)"; fail=1; fi
}
rm -rf "$W"; mkdir -p "$W"
ids=$(grep -o '^=== [A-Z]*-[0-9]*' "$SPEC" | cut -c5-)
n_ids=$(echo "$ids" | grep -c .)
echo "family $FAM: $n_ids rows: $(echo $ids)"

[ -z "$(g status --porcelain -- PROJECT_PLAN.md)" ]; check pre-plan-clean "$?" 0
g rev-parse HEAD

if [ "$NEG" = "--negative-control" ]; then
  echo "== negative control (asserted): a spec naming a row that does not exist"
  cp PROJECT_PLAN.md "$W/plan.neg.pre"
  printf '=== WF-999\nNo such row.\n' > "$W/spec-missing.md"
  python3 "$TOOL" chunks "$W/spec-missing.md"
  check neg-missing-row-refused "$?" 1
  cmp PROJECT_PLAN.md "$W/plan.neg.pre"; check neg-plan-unchanged "$?" 0
  [ ! -e docs/planning/chunks/WF-999.md ]; check neg-nothing-written "$?" 0
fi

echo "== move"
python3 "$TOOL" chunks "$SPEC"
check tool-exit "$?" 0

echo "== (i) re-extraction from git HEAD vs chunk-file body"
for id in $ids; do
  python3 - "$id" "$W" <<'EOF'
import subprocess, sys
cid, w = sys.argv[1], sys.argv[2]
env = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "safe.directory",
       "GIT_CONFIG_VALUE_0": "/workspace", "PATH": "/usr/bin:/bin"}
head = subprocess.run(["git", "show", "HEAD:PROJECT_PLAN.md"], capture_output=True,
                      check=True, env=env).stdout
pre = f"| `{cid}` |".encode()
old = [l for l in head.split(b"\n") if l.startswith(pre)]
new = [l for l in open("PROJECT_PLAN.md", "rb").read().split(b"\n") if l.startswith(pre)]
assert len(old) == 1 and len(new) == 1, (len(old), len(new))
old, new = old[0], new[0]
marker = f"*History: `docs/planning/chunks/{cid}.md`.* ".encode()
k = new.find(marker)
assert k > 0, "pointer missing from the new row"
suffix = new[k + len(marker):]
assert old.endswith(suffix), "trailing cells changed"
span = old[len(pre):len(old) - len(suffix)]
body = open(f"docs/planning/chunks/{cid}.md", "rb").read().split(b"\n\n", 1)[1]
assert body.endswith(b"\n")
open(f"{w}/{cid}.git-span", "wb").write(span)
open(f"{w}/{cid}.chunk-body", "wb").write(body[:-1])
print(f"{cid}: HEAD row {len(old)} B -> new row {len(new)} B; span {len(span)} B")
EOF
  check "i-$id-reextract" "$?" 0
  cmp "$W/$id.git-span" "$W/$id.chunk-body"; check "i-$id-cmp" "$?" 0
done

echo "== (iii) diff shape"
g diff --numstat -- PROJECT_PLAN.md
[ "$(g diff --numstat -- PROJECT_PLAN.md)" = "$(printf '%s\t%s\tPROJECT_PLAN.md' "$n_ids" "$n_ids")" ]
check iii-one-line-per-row "$?" 0
g status --porcelain --untracked-files=all
# The harness's own outputs (this run's log, its test-results row) are not the move.
others=$(g status --porcelain --untracked-files=all | grep -v '^ M PROJECT_PLAN.md$' \
  | grep -v '^?? docs/planning/chunks/[A-Z]*-[0-9]*\.md$' \
  | grep -v '^?? docs/testing/logs/[^/]*\.log$' | grep -v '^ M docs/testing/test-results.md$' | grep -c .)
[ "$others" = 0 ]; check iii-no-other-changes "$?" 0
new_files=$(g status --porcelain --untracked-files=all | grep -c '^?? docs/planning/chunks/')
[ "$new_files" = "$n_ids" ]; check iii-one-new-file-per-row "$?" 0

echo "== (ii) leak check on the staged move (scratch index)"
cp .git/index "$W/index"; mkdir -p "$W/objects"
export GIT_INDEX_FILE=/workspace/$W/index GIT_OBJECT_DIRECTORY=/workspace/$W/objects \
       GIT_ALTERNATE_OBJECT_DIRECTORIES=/workspace/.git/objects
g add PROJECT_PLAN.md $(for id in $ids; do echo "docs/planning/chunks/$id.md"; done)
staged=$(g diff --cached --name-only | grep -c .)
echo "staged in scratch index: $staged paths"
[ "$staged" = $((n_ids + 1)) ]; check ii-git-sees-staged-move "$?" 0
env "${SAFE[@]}" python3 scripts/testing/check_private_leak.py
check ii-leak-check "$?" 0
unset GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES

chown "$HOST_UID:$HOST_GID" docs/planning/chunks docs/planning/chunks/*.md
ls -ln docs/planning/chunks | head -3
wc -c PROJECT_PLAN.md
echo "== summary: fail=$fail"
exit $fail
