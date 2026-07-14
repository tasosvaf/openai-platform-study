#!/usr/bin/env bash
# Run a SWE-bench Lite assignment experiment: easy | medium | hard | all.
#
# Usage:
#   ./run_experiment.sh                 # runs all three (2 workers)
#   ./run_experiment.sh easy            # run just the easy one
#   ./run_experiment.sh all 3           # all three, 3 workers
#   ./run_experiment.sh hard 2 --local  # build images locally (Apple Silicon)
#
# --local can appear in any position; it adds `--namespace ''` so images are
# built locally instead of pulled (required on ARM / M-series Macs).
set -eo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Parse args: pull out --local, keep positionals for level + workers.
POSITIONAL=()
LOCAL=0
for a in "$@"; do
  if [ "$a" = "--local" ]; then LOCAL=1; else POSITIONAL+=("$a"); fi
done
LEVEL="${POSITIONAL[0]:-all}"
MAX_WORKERS="${POSITIONAL[1]:-2}"
DATASET="princeton-nlp/SWE-bench_Lite"
CACHE_LEVEL="env"

NAMESPACE_ARG=()
if [ "$LOCAL" -eq 1 ]; then NAMESPACE_ARG=(--namespace ""); fi

# Prefer the folder-local .venv if present, else fall back to PATH python.
if [ -x "$DIR/.venv/bin/python" ]; then
  PY="$DIR/.venv/bin/python"
else
  PY="$(command -v python3 || command -v python)"
fi

# Pre-flight checks
"$PY" -c "import swebench" 2>/dev/null || { echo "ERROR: 'swebench' not installed in this Python. See README.md > Setup."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker CLI not found. Install Docker and start it (docker run hello-world)."; exit 1; }

if [ "$LEVEL" = "all" ]; then
  LEVELS=(easy medium hard)
else
  LEVELS=("$LEVEL")
fi

rc=0
for lvl in "${LEVELS[@]}"; do
  echo ""
  echo "=== Running '$lvl' experiment (predictions/$lvl.jsonl) ==="
  if ! "$PY" -m swebench.harness.run_evaluation \
    --dataset_name "$DATASET" \
    --predictions_path "predictions/$lvl.jsonl" \
    --max_workers "$MAX_WORKERS" \
    --cache_level "$CACHE_LEVEL" \
    --run_id "assignment-$lvl" \
    "${NAMESPACE_ARG[@]}"; then
    echo "WARNING: '$lvl' experiment returned a non-zero exit code."
    rc=1
  fi
done

echo ""
echo "Done. Summary report(s): <model>.assignment-*.json  |  Detailed logs: logs/run_evaluation/"
exit $rc
