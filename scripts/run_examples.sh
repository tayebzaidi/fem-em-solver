#!/usr/bin/env bash
set -euo pipefail

# Run one or more example scripts inside docker compose without entering container.
#
# Usage:
#   ./scripts/run_examples.sh --list
#   ./scripts/run_examples.sh -e 1                # magnetostatics example 1
#   ./scripts/run_examples.sh -e 1,3 -n 4         # magnetostatics examples 1 and 3
#   ./scripts/run_examples.sh -e mri:1            # MRI example 1 (complex build)
#   ./scripts/run_examples.sh -e mesh:1           # meshing example 1 (real build)
#   ./scripts/run_examples.sh -e mat:1            # materials example 1 (complex build)
#   ./scripts/run_examples.sh -e th:1             # time-harmonic example 1 (complex build)
#   ./scripts/run_examples.sh -e all-mag          # all magnetostatics examples
#   ./scripts/run_examples.sh -e all -n 2         # everything (magnetostatics + MRI + meshing + materials + time-harmonic)
#
# Options:
#   -e, --example   Selection: number (magnetostatics), 'mri:<number>',
#                   'mesh:<number>', 'mat:<number>', 'th:<number>', CSV of any,
#                   'all-mag' (magnetostatics only), or 'all' (everything)
#   -n, --nproc     MPI process count (default: 2)
#   -t, --timeout   Per-example timeout in seconds inside the container (default: 1200)
#   --dry-run       Print the container commands without executing them
#   --list          List available examples and exit
#
# MRI, materials and time-harmonic examples solve in the frequency domain and are
# automatically run with the complex DolfinX build sourced
# (/usr/local/bin/dolfinx-complex-mode); the magnetostatics and meshing examples
# run in the default real build. The
# meshing examples do not solve at all — they build a gated fixture, assert its
# closed-form geometric identities, and export the tags for ParaView.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MAG_DIR="$ROOT_DIR/examples/magnetostatics"
MRI_DIR="$ROOT_DIR/examples/mri"
MESH_DIR="$ROOT_DIR/examples/meshing"
MAT_DIR="$ROOT_DIR/examples/materials"
TH_DIR="$ROOT_DIR/examples/time_harmonic"
DEFAULT_COMPOSE_FILE="$ROOT_DIR/docker/docker-compose.yml"
COMPLEX_MODE_SOURCE="/usr/local/bin/dolfinx-complex-mode"

if [[ -z "${COMPOSE_FILE:-}" && -f "$DEFAULT_COMPOSE_FILE" ]]; then
  export COMPOSE_FILE="$DEFAULT_COMPOSE_FILE"
fi

NPROC=2
TIMEOUT_S=1200
EXAMPLE_SPEC=""
MODE="run"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -e|--example)
      EXAMPLE_SPEC="${2:-}"
      [[ -n "$EXAMPLE_SPEC" ]] || { echo "--example requires a value" >&2; exit 2; }
      shift 2
      ;;
    -n|--nproc)
      NPROC="${2:-}"
      [[ "$NPROC" =~ ^[1-9][0-9]*$ ]] || { echo "--nproc must be a positive integer" >&2; exit 2; }
      shift 2
      ;;
    -t|--timeout)
      TIMEOUT_S="${2:-}"
      [[ "$TIMEOUT_S" =~ ^[1-9][0-9]*$ ]] || { echo "--timeout must be a positive integer (seconds)" >&2; exit 2; }
      if (( TIMEOUT_S > 1200 )); then
        echo "--timeout may not exceed 1200 s (project compute budget, PROJECT_PLAN.md §5)" >&2
        exit 2
      fi
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --list)
      MODE="list"
      shift
      ;;
    -h|--help)
      sed -n '4,24p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

mapfile -t MAG_AVAILABLE < <(find "$MAG_DIR" -maxdepth 1 -type f -name '*.py' | sort)
mapfile -t MRI_AVAILABLE < <(find "$MRI_DIR" -maxdepth 1 -type f -name '*.py' 2>/dev/null | sort)
mapfile -t MESH_AVAILABLE < <(find "$MESH_DIR" -maxdepth 1 -type f -name '*.py' 2>/dev/null | sort)
mapfile -t MAT_AVAILABLE < <(find "$MAT_DIR" -maxdepth 1 -type f -name '*.py' 2>/dev/null | sort)
mapfile -t TH_AVAILABLE < <(find "$TH_DIR" -maxdepth 1 -type f -name '*.py' 2>/dev/null | sort)

if [[ ${#MAG_AVAILABLE[@]} -eq 0 && ${#MRI_AVAILABLE[@]} -eq 0 \
      && ${#MESH_AVAILABLE[@]} -eq 0 && ${#MAT_AVAILABLE[@]} -eq 0 \
      && ${#TH_AVAILABLE[@]} -eq 0 ]]; then
  echo "No examples found in $MAG_DIR, $MRI_DIR, $MESH_DIR, $MAT_DIR or $TH_DIR" >&2
  exit 1
fi

list_group() {
  local title="$1" prefix="$2"; shift 2
  echo "$title"
  local p b num
  for p in "$@"; do
    b="$(basename "$p")"
    num="$((10#${b%%_*}))"
    echo "  ${prefix}${num} -> ${p#$ROOT_DIR/}"
  done
}

if [[ "$MODE" == "list" ]]; then
  echo "Available examples:"
  list_group "magnetostatics (default real build):" "" "${MAG_AVAILABLE[@]}"
  if [[ ${#MRI_AVAILABLE[@]} -gt 0 ]]; then
    list_group "mri (complex build, sourced automatically):" "mri:" "${MRI_AVAILABLE[@]}"
  fi
  if [[ ${#MESH_AVAILABLE[@]} -gt 0 ]]; then
    list_group "meshing (default real build, no solve):" "mesh:" "${MESH_AVAILABLE[@]}"
  fi
  if [[ ${#MAT_AVAILABLE[@]} -gt 0 ]]; then
    list_group "materials (complex build, sourced automatically):" "mat:" "${MAT_AVAILABLE[@]}"
  fi
  if [[ ${#TH_AVAILABLE[@]} -gt 0 ]]; then
    list_group "time-harmonic (complex build, sourced automatically):" "th:" "${TH_AVAILABLE[@]}"
  fi
  echo
  echo "Selections: -e <n> | -e mri:<n> | -e mesh:<n> | -e mat:<n> | -e th:<n> | -e all-mag | -e all"
  exit 0
fi

if [[ -z "$EXAMPLE_SPEC" ]]; then
  echo "Missing --example selection. Use --list to see available options." >&2
  exit 2
fi

# SELECTED entries are "<group>|<path>" with group in {mag, mri, mesh, mat, th}.
SELECTED=()
declare -A SEEN=()

select_path() {
  local group="$1" path="$2"
  [[ -f "$path" ]] || return 0
  if [[ -z "${SEEN[$path]:-}" ]]; then
    SELECTED+=("${group}|${path}")
    SEEN[$path]=1
  fi
}

select_by_number() {
  local group="$1" dir="$2" token="$3"
  local num_padded matches m
  num_padded=$(printf "%02d" "$((10#$token))")
  matches=("$dir/${num_padded}"_*.py)
  if [[ ! -e "${matches[0]}" ]]; then
    echo "No ${group} example found for number: $token" >&2
    exit 2
  fi
  for m in "${matches[@]}"; do
    select_path "$group" "$m"
  done
}

case "$EXAMPLE_SPEC" in
  all)
    for p in "${MAG_AVAILABLE[@]}"; do select_path mag "$p"; done
    for p in "${MRI_AVAILABLE[@]}"; do select_path mri "$p"; done
    for p in "${MESH_AVAILABLE[@]}"; do select_path mesh "$p"; done
    for p in "${MAT_AVAILABLE[@]}"; do select_path mat "$p"; done
    for p in "${TH_AVAILABLE[@]}"; do select_path th "$p"; done
    ;;
  all-mag|all-magnetostatics)
    for p in "${MAG_AVAILABLE[@]}"; do select_path mag "$p"; done
    ;;
  *)
    IFS=',' read -r -a TOKENS <<< "$EXAMPLE_SPEC"
    for t in "${TOKENS[@]}"; do
      token="$(echo "$t" | xargs)"
      if [[ "$token" =~ ^mri:([0-9]+)$ ]]; then
        select_by_number mri "$MRI_DIR" "${BASH_REMATCH[1]}"
      elif [[ "$token" =~ ^mesh:([0-9]+)$ ]]; then
        select_by_number mesh "$MESH_DIR" "${BASH_REMATCH[1]}"
      elif [[ "$token" =~ ^mat:([0-9]+)$ ]]; then
        select_by_number mat "$MAT_DIR" "${BASH_REMATCH[1]}"
      elif [[ "$token" =~ ^th:([0-9]+)$ ]]; then
        select_by_number th "$TH_DIR" "${BASH_REMATCH[1]}"
      elif [[ "$token" =~ ^[0-9]+$ ]]; then
        select_by_number mag "$MAG_DIR" "$token"
      else
        echo "Invalid example token: '$token' (expected <n>, mri:<n>, mesh:<n>, mat:<n>, th:<n>, all-mag, or all)" >&2
        exit 2
      fi
    done
    ;;
esac

cd "$ROOT_DIR"

echo "Running ${#SELECTED[@]} example(s) with mpiexec -n $NPROC (timeout ${TIMEOUT_S}s each)"
echo "COMPOSE_FILE=${COMPOSE_FILE:-<unset>}"

for entry in "${SELECTED[@]}"; do
  group="${entry%%|*}"
  ex="${entry#*|}"
  rel="${ex#$ROOT_DIR/}"
  prefix=""
  if [[ "$group" == "mri" || "$group" == "mat" || "$group" == "th" ]]; then
    prefix="source $COMPLEX_MODE_SOURCE && "
  fi
  inner="cd /workspace && ${prefix}PYTHONPATH=/workspace/src timeout $TIMEOUT_S mpiexec -n $NPROC python3 $rel"
  echo
  echo "==> $rel${prefix:+ (complex build)}"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "  [dry-run] docker compose exec fem-em-solver bash -lc \"$inner\""
  else
    docker compose exec fem-em-solver bash -lc "$inner"
  fi
done

echo
echo "Done."
