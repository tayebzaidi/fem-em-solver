#!/usr/bin/env bash
# Heartbeat for a long compute window (`OPS-43`).
#
# A direct solve is silent for its whole factorization, so a harness log can go
# half an hour without a line while the run is perfectly healthy — and when a
# wrapper dies, nothing records what the run was doing at the time. This samples
# the container from *outside* the run, so it works even when the process says
# nothing and survives the run's own death.
#
#   scripts/testing/watch_run.sh <service> <out-file> [interval_s]
#
# Writes one TSV row per sample: UTC time, elapsed, cgroup memory current and
# peak (GiB), rank count, and summed rank CPU%. Exits when the ranks are gone.
# Read the memory column as the progress bar a direct solve does not have:
# it climbs through the factorization and plateaus when it completes.
#
# Do NOT wrap this in `timeout`: it kills the process group and the docker
# calls come back empty, which the loop reads as "container unreachable" and
# exits on. It ends by itself when the ranks do; background it instead.
#
# Note (§5.1): `memory.peak` is per *container lifetime* and cannot be reset on
# this kernel, so the peak column is only attributable to this run if the
# service was restarted immediately before it. The header records whether it
# was, by reading the container's start time.
set -uo pipefail

SERVICE="${1:?usage: watch_run.sh <service> <out-file> [interval_s]}"
OUT="${2:?usage: watch_run.sh <service> <out-file> [interval_s]}"
INTERVAL="${3:-60}"
START_EPOCH="$(date -u +%s)"

container_start="$(docker inspect "$SERVICE" --format '{{.State.StartedAt}}' 2>/dev/null || echo unknown)"
{
  echo "# watch_run.sh — service=$SERVICE interval=${INTERVAL}s"
  echo "# container started: $container_start"
  echo "# peak is per container lifetime (§5.1); attributable to this run only"
  echo "# if the service was restarted immediately before the window."
  printf '# %s\t%s\t%s\t%s\t%s\t%s\n' utc elapsed_s mem_gib peak_gib ranks cpu_pct
} > "$OUT"

while true; do
  cur="$(docker exec "$SERVICE" sh -c 'cat /sys/fs/cgroup/memory.current' 2>/dev/null)"
  if [[ -z "$cur" ]]; then
    echo "# $(date -u +%H:%M:%S) container unreachable — stopping" >> "$OUT"
    break
  fi
  peak="$(docker exec "$SERVICE" sh -c 'cat /sys/fs/cgroup/memory.peak' 2>/dev/null || echo 0)"
  ranks="$(docker exec "$SERVICE" sh -c 'ps -eo comm | grep -c "^python3$"' 2>/dev/null || echo 0)"
  cpu="$(docker exec "$SERVICE" sh -c "ps -eo pcpu,comm | awk '\$2==\"python3\"{s+=\$1} END{printf \"%.0f\", s}'" 2>/dev/null || echo 0)"
  printf '%s\t%s\t%.1f\t%.1f\t%s\t%s\n' \
    "$(date -u +%H:%M:%S)" \
    "$(( $(date -u +%s) - START_EPOCH ))" \
    "$(awk -v b="$cur" 'BEGIN{print b/1073741824}')" \
    "$(awk -v b="$peak" 'BEGIN{print b/1073741824}')" \
    "$ranks" "$cpu" >> "$OUT"
  if [[ "${ranks:-0}" -eq 0 ]]; then
    echo "# $(date -u +%H:%M:%S) ranks exited after $(( $(date -u +%s) - START_EPOCH )) s" >> "$OUT"
    break
  fi
  sleep "$INTERVAL"
done
