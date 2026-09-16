#!/usr/bin/env bash
# checkin.sh — "update summary since last check-in", with no Claude session.
#
# Prints what the scheduled automation has done since a marker (default: the
# last time this script was run with --mark, else 24 h): commits, every
# launcher log's exit status and final message, the attempts.md entries, the
# dashboard's Waiting-on-you list and the §9 On-deck queue. Read-only apart
# from the gitignored marker file.
#
# Zero-token use from inside a Claude Code session: type
#     ! scripts/automation/checkin.sh
# in the prompt. The `!` prefix runs the command locally and drops its output
# into the conversation without a model turn. (A /checkin slash command with
# `!`-injection would also work but sends the output to the model as a prompt,
# which costs a reply.)
#
#   checkin.sh [--since <ref|date|Nh|Nd>] [--full] [--mark] [--no-logs]
#     --since   git ref or date understood by `date -d` ("3d", "12h",
#               "2026-09-13 18:00"), or a commit whose date is used.
#     --full    print whole launcher-log final messages (default ~20 lines)
#               and the full attempts.md entries (default: headings only).
#     --mark    after printing, record now as the next default `--since`.
#   Whatever --since resolves to, the window is widened to at least 12 h.
#     --no-logs skip the launcher-log section.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"
MARKER="$REPO/logs/automation/.checkin-marker"
LOGDIR="$REPO/logs/automation"
FULL=0; MARK=0; LOGS=1; SINCE=""
MAXLINES=20

while [ $# -gt 0 ]; do
  case "$1" in
    --since) SINCE="$2"; shift 2 ;;
    --full) FULL=1; shift ;;
    --mark) MARK=1; shift ;;
    --no-logs) LOGS=0; shift ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ---- resolve --since to an epoch --------------------------------------------
if [ -z "$SINCE" ]; then
  if [ -f "$MARKER" ]; then SINCE_EPOCH="$(cat "$MARKER")"; SINCE_SRC="last --mark"
  else SINCE_EPOCH="$(date -d '24 hours ago' +%s)"; SINCE_SRC="default 24h (no marker)"; fi
elif [[ "$SINCE" =~ ^([0-9]+)([hd])$ ]]; then
  n="${BASH_REMATCH[1]}"; u="${BASH_REMATCH[2]}"
  [ "$u" = h ] && SINCE_EPOCH="$(date -d "$n hours ago" +%s)" || SINCE_EPOCH="$(date -d "$n days ago" +%s)"
  SINCE_SRC="--since $SINCE"
elif git rev-parse --verify -q "$SINCE^{commit}" >/dev/null 2>&1; then
  SINCE_EPOCH="$(git log -1 --format=%ct "$SINCE")"; SINCE_SRC="commit $(git rev-parse --short "$SINCE")"
else
  SINCE_EPOCH="$(date -d "$SINCE" +%s)" || { echo "cannot parse --since '$SINCE'" >&2; exit 2; }
  SINCE_SRC="--since '$SINCE'"
fi
# Floor: never show less than the last 12 h, whatever the marker says.
FLOOR_EPOCH="$(date -d '12 hours ago' +%s)"
if [ "$SINCE_EPOCH" -gt "$FLOOR_EPOCH" ]; then SINCE_EPOCH="$FLOOR_EPOCH"; SINCE_SRC="$SINCE_SRC → 12 h floor"; fi
SINCE_ISO="$(date -d "@$SINCE_EPOCH" '+%Y-%m-%d %H:%M %Z')"
SINCE_UTC="$(date -u -d "@$SINCE_EPOCH" '+%Y-%m-%dT%H:%MZ')"

hr() { printf '\n== %s\n' "$1"; }

# ---- header -------------------------------------------------------------------
echo "CHECK-IN  now $(date '+%Y-%m-%d %H:%M %Z')  |  since $SINCE_ISO ($SINCE_SRC)"
DIRTY="$(git status --porcelain | wc -l)"
printf 'HEAD %s  %s\n' "$(git rev-parse --short HEAD)" "$([ "$DIRTY" = 0 ] && echo 'tree clean' || echo "TREE DIRTY ($DIRTY paths)")"
BR="$(git branch --list 'attempt/*' 'recovered/*' | sed 's/^[* ] *//' | tr '\n' ' ')"
[ -n "$BR" ] && echo "parked branches: $BR"
git branch --list 'recovered/*' | grep -q . && echo "!! recovered/* present — a session died with a dirty tree"
if command -v docker >/dev/null 2>&1; then
  docker compose -f docker/docker-compose.yml ps --format '{{.Name}} {{.Status}}' 2>/dev/null | head -2
fi

# ---- commits -----------------------------------------------------------------
hr "commits since (newest first)"
git log --since="@$SINCE_EPOCH" --format='%h %ad %s' --date='format:%m-%d %H:%M' | cut -c1-150
[ "$(git log --since="@$SINCE_EPOCH" --oneline | wc -l)" = 0 ] && echo "(none)"

# ---- launcher logs -------------------------------------------------------------
if [ "$LOGS" = 1 ]; then
  hr "automation runs since (logs/automation)"
  found=0
  for f in $(ls -tr "$LOGDIR"/*.log 2>/dev/null); do
    base="$(basename "$f")"
    ts="${base%%_*}"                        # 20260914T093001Z
    start_epoch="$(date -u -d "${ts:0:4}-${ts:4:2}-${ts:6:2}T${ts:9:2}:${ts:11:2}:${ts:13:2}Z" +%s 2>/dev/null)" || continue
    end_epoch="$(stat -c %Y "$f")"
    [ "$end_epoch" -lt "$SINCE_EPOCH" ] && continue
    found=1
    kind="${base#*_}"; kind="${kind%.log}"
    exitline="$(grep -o 'exit=[0-9]*' "$f" | tail -1)"
    skipped=""; grep -q 'holds the lock; skipping' "$f" && skipped=" SKIPPED(lock)"
    dur=$(( (end_epoch - start_epoch) / 60 ))
    printf '\n-- %s  %s  %s  %dm  %s%s  (%s bytes)\n' \
      "$(date -d "@$start_epoch" '+%a %m-%d %H:%M')" "$kind" "${exitline:-running?}" "$dur" \
      "$(grep -o 'model=[^ ]*' "$f" | tail -1)" "$skipped" "$(stat -c %s "$f")"
    [ "$(stat -c %s "$f")" -lt 200 ] && { sed 's/^/   /' "$f"; continue; }
    # Final assistant message = everything between the last launcher stamp
    # line before the body and the trailing "exit=" line.
    body="$(grep -v -E '^(Mon|Tue|Wed|Thu|Fri|Sat|Sun) [A-Z][a-z]{2} +[0-9]+ [0-9:]+ UTC [0-9]{4} ' "$f" \
            | grep -v -E 'Gmail, Google Calendar|need (to be )?authoris|need authoriz|Unavailable connectors' \
            | sed '/^[[:space:]]*$/N;/^\n$/D')"
    if [ "$FULL" = 1 ]; then printf '%s\n' "$body" | sed 's/^/   /'
    else
      n="$(printf '%s\n' "$body" | wc -l)"
      printf '%s\n' "$body" | head -n "$MAXLINES" | cut -c1-200 | sed 's/^/   /'
      [ "$n" -gt "$MAXLINES" ] && echo "   … (+$((n - MAXLINES)) lines; --full)"
    fi
  done
  [ "$found" = 0 ] && echo "(no launcher logs finished since $SINCE_ISO)"
fi

# ---- attempts journal ---------------------------------------------------------
hr "attempts.md entries since $SINCE_UTC"
# Entry headings start "## <UTC timestamp>"; compare lexically on the ISO stamp.
awk -v since="$SINCE_UTC" -v full="$FULL" '
  /^## 20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]T/ {
    stamp=$2; on = (stamp >= since); if (on) { n++; print; } next }
  on && full { print }
  END { if (!n) print "(none)" }' docs/testing/attempts.md | cut -c1-220

# ---- daily review: dashboard digest ----------------------------------------------
hr "dashboard (docs/status/dashboard.md)"
sed -n '3,4p' docs/status/dashboard.md | cut -c1-200
echo
# Join each numbered item's wrapped lines, then cut to one line.
awk '/^## Waiting on you/{on=1; next} /^## /{on=0} !on{next}
     /^[0-9]+\. /{if(cur!="")print cur; cur=$0; next}
     /^[[:space:]]+[^[:space:]]/ && cur!="" {sub(/^[[:space:]]+/," "); cur=cur $0; next}
     {if(cur!="")print cur; cur=""}
     END{if(cur!="")print cur}' docs/status/dashboard.md | cut -c1-170 | sed 's/^/   /'
echo
grep -E '^## On deck' docs/status/dashboard.md | sed 's/^## //'

# ---- §9 On deck (source of truth) ----------------------------------------------
hr "§9 On deck (PROJECT_PLAN.md) — the queue"
# The queue proper starts after the "Predicted slot-minutes … running total" line.
awk '/^### On deck/{on=1} /^## 10\./{on=0} !on{next}
     /^\*\*Predicted slot-minutes/{q=1; getline; print "total: " $0; next}
     q && /^[0-9]+\. /{if(cur!="")print cur; cur=$0; next}
     q && /^[[:space:]]+[^[:space:]]/ && cur!="" {sub(/^[[:space:]]+/," "); cur=cur $0; next}
     q {if(cur!="")print cur; cur=""}
     END{if(cur!="")print cur}' PROJECT_PLAN.md \
  | awk '/^[0-9]+\. .*(DONE|✅)/ { n=$1; match($0,/DONE[^(]*/); slot=substr($0,RSTART,RLENGTH); gsub(/\*/,"",slot);
                                 match($0,/`[A-Z]+-[0-9]+[^`]*`/); id=substr($0,RSTART,RLENGTH);
                                 print n " " slot " " id; next }
         { print substr($0,1,220) }' | sed 's/^/   /'

# ---- next scheduled fires ---------------------------------------------------------
hr "schedule"
echo "active days Sun Mon Wed Fri Sat: review 03:00, slots 04:30/06:00/07:30/09:00; weekly Sat 21:00; XL 02:00 Sun–Fri, XXL 02:00 Sat"
for q in xl xxl; do
  f="docs/testing/${q}-queue.env"; d="docs/testing/${q}-queue.d"
  c="$(grep -o '^XL_CHUNK="[^"]*"' "$f" 2>/dev/null | cut -d'"' -f2)"
  files="$(ls "$d"/*.env 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/\.env$//' | tr '\n' ' ')"
  echo "$q queue: ${c:+legacy=$c }${files:-empty}"
done
LEDGER_LAST="$(grep -E '^\| *20[0-9]{2}-' docs/testing/xl-ledger.md 2>/dev/null | tail -1 | cut -c1-160)"
[ -n "$LEDGER_LAST" ] && echo "xl ledger last row: $LEDGER_LAST"

if [ "$MARK" = 1 ]; then
  mkdir -p "$LOGDIR"; date +%s > "$MARKER"
  echo; echo "(marker set: next default --since is now)"
fi
