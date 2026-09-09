#!/usr/bin/env bash
# What is using this box right now — CPU and memory, from every source visible
# to an agent session (`OPS-43`, operator direction 2026-09-09).
#
#   scripts/testing/box_check.sh [ranks_wanted]
#
# Exit 0 = the visible box has room for `ranks_wanted` (default 16).
# Exit 1 = visibly busy, postpone.
# Exit 2 = could not measure (fails loud here; the guard fails open).
#
# ---------------------------------------------------------------------------
# READ THIS BEFORE TRUSTING A GREEN RESULT.
#
# This is WSL2. `/proc/loadavg`, `nproc` and `free` describe **this Linux VM
# only**. Work running on the Windows host, in another WSL distro, or in
# another VM is **invisible here** and this script cannot see it. That is not a
# gap that can be closed from inside the sandbox: there is no `powershell.exe`
# on PATH and `/mnt` is not readable, so the host cannot be probed at all.
#
# Measured on 2026-09-09: the operator's Task Manager showed 100% CPU with two
# solves running while this VM reported load 0.84 and both project containers
# at 0.00%. A load-average check would have called the box free and started a
# 16-rank, 2-hour window straight into it.
#
# So: a green result here means "nothing *I* can see is using the box". Only a
# human looking at the host can turn that into "the box is free".
# ---------------------------------------------------------------------------
set -uo pipefail

RANKS="${1:-16}"
HEADROOM=4
status=0

printf '=== containers (Docker sees these; 100%% = one core) ===\n'
stats="$(docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' 2>/dev/null)"
if [[ -z "$stats" ]]; then
  # Measured 2026-09-09: the docker socket is reachable from a direct agent
  # command but NOT from inside a script in this sandbox. So this section goes
  # blank exactly when it is run the convenient way, and the container numbers
  # have to come from a direct `docker stats --no-stream` instead. Say so
  # rather than reporting zero, which would read as "idle".
  echo "  UNAVAILABLE — no running containers, or the docker socket is not"
  echo "  reachable from inside a script here. Run this instead, directly:"
  echo "      docker stats --no-stream"
  container_cores=0
else
  printf '%s\n' "$stats" | sed 's/^/  /'
  container_cores="$(printf '%s\n' "$stats" | awk -F'\t' '{gsub(/%/,"",$2); s+=$2} END {printf "%.1f", s/100}')"
fi
printf '  -> containers are using %s cores (0 may mean unmeasured — see above)\n\n' "$container_cores"

printf '=== this WSL VM (blind to the Windows host — see header) ===\n'
ncpu="$(nproc)"
read -r l1 l5 l15 _ < /proc/loadavg
printf '  cores %s   load %s / %s / %s (1/5/15 min)\n' "$ncpu" "$l1" "$l5" "$l15"
free -g | awk 'NR==2{printf "  memory %s GiB total, %s used, %s available\n", $2, $3, $7}'

busy="$(awk -v a="$l1" -v b="$container_cores" 'BEGIN{print (a>b)?a:b}')"
free_cores="$(awk -v n="$ncpu" -v b="$busy" 'BEGIN{printf "%.1f", n-b}')"
need=$((RANKS + HEADROOM))
printf '  -> %s cores look free; a %s-rank window wants %s (ranks + %s headroom)\n\n' \
  "$free_cores" "$RANKS" "$need" "$HEADROOM"

if awk -v f="$free_cores" -v n="$need" 'BEGIN{exit !(f < n)}'; then
  printf 'VERDICT: POSTPONE — visibly busy.\n'
  status=1
else
  printf 'VERDICT: nothing visible is using the box.\n'
fi

cat <<'EOF'

BLIND SPOT — the part this script cannot answer:
  Windows-host processes, other WSL distros and other VMs are invisible from
  inside the sandbox (no powershell.exe on PATH, /mnt unreadable). On
  2026-09-09 the host was at 100% CPU with two solves while this VM read
  load 0.84 and both containers 0.00%.
  Before starting an XL window, look at Task Manager yourself.
EOF
exit "$status"
