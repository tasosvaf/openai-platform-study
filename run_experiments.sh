#!/usr/bin/env bash
# Common runner for BOTH benchmarks in this repo.
#
# By default it evaluates the standard 3-experiment set for each benchmark and
# writes the two result sets into subfolders of a single results root:
#
#     <results-root>/QuixBugs_results/<tool>/run_<ts>/     (QuixBugs, 3 programs)
#     <results-root>/SWE-bench_results/<tool>/run_<ts>/    (SWE-bench, 3 levels)
#
# QuixBugs is evaluated by running its pytest suites directly. SWE-bench only
# *collects* the reports produced by its Docker harness; pass --swe-docker to
# also run that Docker evaluation first (otherwise unrun levels show as NOT RUN).
#
# Usage:
#   ./run_experiments.sh                                  # both, default tool/model
#   ./run_experiments.sh --tool aider --model "GPT 5.4-mini"
#   ./run_experiments.sh --only quixbugs                  # just QuixBugs
#   ./run_experiments.sh --only swe --swe-docker          # SWE + run Docker eval
#   ./run_experiments.sh --results-root /path/to/results
#   ./run_experiments.sh --tokens-before 0 --tokens-after 152340 --cost-usd 0.34
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Defaults ---
RESULTS_ROOT="/Users/tasosvaf/repos/testRepos/experiment_results"
TOOL="github_copilot_cli"
MODEL="GPT 5.4-mini"
ONLY="both"          # both | quixbugs | swe
SWE_DOCKER=0
SWE_WORKERS=2
SWE_LOCAL="--local"  # build images locally (Apple Silicon friendly); --no-local to disable
TOKENS_BEFORE=""
TOKENS_AFTER=""
COST_USD=""
NOTES=""

# --- Parse args ---
while [ "$#" -gt 0 ]; do
  case "$1" in
    --tool)          TOOL="$2"; shift 2 ;;
    --model)         MODEL="$2"; shift 2 ;;
    --results-root)  RESULTS_ROOT="$2"; shift 2 ;;
    --only)          ONLY="$2"; shift 2 ;;
    --swe-docker)    SWE_DOCKER=1; shift ;;
    --swe-workers)   SWE_WORKERS="$2"; shift 2 ;;
    --no-local)      SWE_LOCAL=""; shift ;;
    --tokens-before) TOKENS_BEFORE="$2"; shift 2 ;;
    --tokens-after)  TOKENS_AFTER="$2"; shift 2 ;;
    --cost-usd)      COST_USD="$2"; shift 2 ;;
    --notes)         NOTES="$2"; shift 2 ;;
    -h|--help)       sed -n '2,26p' "$0"; exit 0 ;;
    *) echo "ERROR: unknown option '$1' (see --help)."; exit 2 ;;
  esac
done

case "$ONLY" in both|quixbugs|swe) ;; *) echo "ERROR: --only must be both|quixbugs|swe."; exit 2 ;; esac

QUIX_RESULTS="$RESULTS_ROOT/QuixBugs_results"
SWE_RESULTS="$RESULTS_ROOT/SWE-bench_results"

# Shared token/cost args passed through to both evaluators.
COMMON_ARGS=(--tool "$TOOL" --model "$MODEL")
[ -n "$TOKENS_BEFORE" ] && COMMON_ARGS+=(--tokens-before "$TOKENS_BEFORE")
[ -n "$TOKENS_AFTER" ]  && COMMON_ARGS+=(--tokens-after "$TOKENS_AFTER")
[ -n "$COST_USD" ]      && COMMON_ARGS+=(--cost-usd "$COST_USD")
[ -n "$NOTES" ]         && COMMON_ARGS+=(--notes "$NOTES")

echo "Results root : $RESULTS_ROOT"
echo "Tool / model : $TOOL / $MODEL"
echo "Scope        : $ONLY"
echo ""

rc=0

if [ "$ONLY" = "both" ] || [ "$ONLY" = "quixbugs" ]; then
  echo "=== QuixBugs: evaluating the default 3 programs ==="
  ( cd "$DIR/QuixBugs_experiments" \
      && python3 harness/experiment_runner.py evaluate \
           "${COMMON_ARGS[@]}" --results-dir "$QUIX_RESULTS" ) || rc=1
  echo ""
fi

if [ "$ONLY" = "both" ] || [ "$ONLY" = "swe" ]; then
  if [ "$SWE_DOCKER" -eq 1 ]; then
    echo "=== SWE-bench: running Docker evaluation (all 3 levels) ==="
    LOCAL_ARG=()
    [ -n "$SWE_LOCAL" ] && LOCAL_ARG=("$SWE_LOCAL")
    ( cd "$DIR/SWE-bench_experiments" \
        && ./run_experiment.sh all "$SWE_WORKERS" "${LOCAL_ARG[@]}" ) || rc=1
  fi
  echo "=== SWE-bench: collecting the default 3 levels ==="
  ( cd "$DIR/SWE-bench_experiments" \
      && python3 harness/swe_experiment_runner.py evaluate \
           "${COMMON_ARGS[@]}" --results-dir "$SWE_RESULTS" ) || rc=1
  echo ""
fi

echo "----------------------------------------------------------------------"
echo "Done. Results:"
[ "$ONLY" != "swe" ]      && echo "  QuixBugs  -> $QUIX_RESULTS/$TOOL/"
[ "$ONLY" != "quixbugs" ] && echo "  SWE-bench -> $SWE_RESULTS/$TOOL/"
exit $rc
