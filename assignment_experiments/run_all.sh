#!/usr/bin/env bash
# One-shot wrapper for macOS + Colima (Apple Silicon friendly).
#
# It does the whole flow for you:
#   1. Ensures the Colima Docker VM is running (starts it if needed).
#   2. Points DOCKER_HOST at Colima's socket (swebench uses docker.from_env()).
#   3. Activates the local .venv (created during setup).
#   4. Runs the chosen experiment(s) via run_experiment.sh with --local.
#
# Usage:
#   ./run_all.sh                    # run all three levels (2 workers)
#   ./run_all.sh easy               # run only easy
#   ./run_all.sh medium             # run only medium
#   ./run_all.sh hard               # run only hard
#   ./run_all.sh all 3              # all three, 3 workers
#   ./run_all.sh easy 2 --no-local  # pull prebuilt images instead of building locally
#
# Options:
#   LEVEL       easy | medium | hard | all           (default: all)
#   WORKERS     max parallel workers                 (default: 2)
#   --no-local  do NOT pass --local (use on Intel Macs to pull prebuilt x86_64 images)
#   --cpu N     Colima CPUs when starting it         (default: 8)
#   --memory N  Colima memory in GiB when starting   (default: 12)
#   --disk N    Colima disk in GiB when starting     (default: 100)
set -eo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# --- Defaults ---
LEVEL="all"
WORKERS="2"
USE_LOCAL=1
COLIMA_CPU=8
COLIMA_MEM=12
COLIMA_DISK=100

# --- Parse args (positional level/workers + flags in any order) ---
POSITIONAL=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --no-local) USE_LOCAL=0; shift ;;
    --cpu)      COLIMA_CPU="$2"; shift 2 ;;
    --memory)   COLIMA_MEM="$2"; shift 2 ;;
    --disk)     COLIMA_DISK="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,25p' "$0"; exit 0 ;;
    *) POSITIONAL+=("$1"); shift ;;
  esac
done
[ "${#POSITIONAL[@]}" -ge 1 ] && LEVEL="${POSITIONAL[0]}"
[ "${#POSITIONAL[@]}" -ge 2 ] && WORKERS="${POSITIONAL[1]}"

case "$LEVEL" in
  easy|medium|hard|all) ;;
  *) echo "ERROR: LEVEL must be one of: easy | medium | hard | all (got '$LEVEL')."; exit 2 ;;
esac

# --- 1. Ensure Colima is running ---
if ! command -v colima >/dev/null 2>&1; then
  echo "ERROR: colima not found. Install it: brew install colima docker"
  exit 1
fi
if colima status >/dev/null 2>&1; then
  echo "Colima already running."
else
  echo "Starting Colima (cpu=$COLIMA_CPU memory=${COLIMA_MEM}G disk=${COLIMA_DISK}G)..."
  colima start --cpu "$COLIMA_CPU" --memory "$COLIMA_MEM" --disk "$COLIMA_DISK" --arch aarch64
fi

# --- 2. Point DOCKER_HOST at Colima's socket ---
SOCK="$(docker context inspect colima --format '{{.Endpoints.docker.Host}}' 2>/dev/null || true)"
if [ -z "$SOCK" ]; then
  SOCK="unix://$HOME/.colima/default/docker.sock"
fi
export DOCKER_HOST="$SOCK"
echo "DOCKER_HOST=$DOCKER_HOST"
docker info >/dev/null 2>&1 || { echo "ERROR: Docker daemon not reachable via Colima."; exit 1; }

# --- 3. Activate the local venv if present ---
if [ -f "$DIR/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$DIR/.venv/bin/activate"
else
  echo "WARNING: .venv not found. See README > Setup. Falling back to system python."
fi

# --- 4. Run the experiment(s) ---
LOCAL_ARG=()
[ "$USE_LOCAL" -eq 1 ] && LOCAL_ARG=(--local)

echo "Running level='$LEVEL' workers='$WORKERS' local=$USE_LOCAL"
./run_experiment.sh "$LEVEL" "$WORKERS" "${LOCAL_ARG[@]}"
