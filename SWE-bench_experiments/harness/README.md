# SWE-bench agent-comparison harness

Companion to the QuixBugs harness (`../../QuixBugs_experiments/harness/`). It
exports the SWE-bench Lite assignment results — the **"second 3"** experiments
(easy/medium/hard) — into a per-tool, comparable result set under:

```
/Users/tasosvaf/repos/testRepos/experiment_results/SWE-bench_results
```

It sits beside the QuixBugs output (`QuixBugs_results`). The two benchmarks are
**separate executions**, so each one's token cost is tracked independently.

```
experiment_results/
├── QuixBugs_results/    <- the "first 3"  (QuixBugs_experiments harness)
└── SWE-bench_results/   <- the "second 3" (this harness)
    ├── github_copilot_cli/
    ├── vscode_copilot_cli/
    ├── cline/
    ├── aider/
    ├── openai_codex_cli/
    └── openai_codex_ui/
```

The three experiments (easy → medium → hard):

| Level | Instance | Repo |
| --- | --- | --- |
| easy | `matplotlib__matplotlib-23563` | matplotlib |
| medium | `sympy__sympy-22005` | sympy |
| hard | `django__django-11019` | django |

---

## Difference from the QuixBugs harness

SWE-bench runs each patch in Docker via `run_experiment.sh` / `run_all.sh`, which
already writes the authoritative reports and logs. So this harness **collects**
those results rather than running tests itself:

- **Runs the tests:** `../run_experiment.sh` (Docker) — see [../README.md](../README.md).
- **Collects + exports:** `harness/swe_experiment_runner.py evaluate`.

---

## The loop for each tool

```bash
cd /Users/tasosvaf/repos/testRepos/openai-platform-study/SWE-bench_experiments

# 1. Put the agent's patch for each level into predictions/<level>.jsonl
#    (set model_patch + model_name_or_path). See ../README.md > "Use your own model".

# 2. Run the SWE-bench evaluation in Docker (produces the reports + logs).
./run_experiment.sh all 2 --local        # or ./run_all.sh on Apple Silicon

# 3. Collect + export the run (records token cost you read from the tool).
python3 harness/swe_experiment_runner.py evaluate \
    --tool aider --model gpt-5.1 \
    --tokens-before 0 --tokens-after 240000 --cost-usd 1.20 \
    --notes "one pass per instance"

# Only a subset of levels:
python3 harness/swe_experiment_runner.py evaluate --tool aider --only easy medium

# Leaderboard across every recorded run:
python3 harness/swe_experiment_runner.py compare
```

`--model` must match the `model_name_or_path` you used in `predictions/*.jsonl`
(that is how the harness finds `<model>.assignment-<level>.json` and the logs).

---

## What gets measured

Automatic, per run:

- **Resolved** — how many of the evaluated instances SWE-bench marked resolved.
- **Resolve rate** — resolved / total.
- **Per-instance status** — resolved / unresolved / empty / error / not-run, plus
  the `FAIL_TO_PASS` and `PASS_TO_PASS` test tallies from `report.json`.
- **Diffs** — the applied patch per instance, under `diffs/<instance_id>.diff`.
- **Token cost** — `tokens_before` / `tokens_after` / `tokens_used` / `cost_usd`
  (you supply the before/after; the harness stores the delta).

You fill in `scorecard.md` (the same 7-criterion rubric as QuixBugs) after
inspecting the run.

---

## Output layout (per run)

```
SWE-bench_results/<tool>/run_<timestamp>/
├── summary.json      # machine-readable everything
├── summary.md        # human summary + per-instance table
├── scorecard.md      # qualitative rubric to fill in
├── tokens.json       # before / after / used / cost
├── test_output.txt   # collected SWE-bench test output per instance
└── diffs/
    ├── matplotlib__matplotlib-23563.diff
    ├── sympy__sympy-22005.diff
    └── django__django-11019.diff
```

## Notes

- If a level shows **NOT RUN**, its SWE-bench report is missing — run
  `./run_experiment.sh <level>` first, then re-collect.
- Token counts are supplied by you (each tool reports them differently); the
  harness records the delta and cost verbatim so runs stay comparable.
- See [prompt.md](prompt.md) for the per-tool task prompt and
  [driver_prompt.md](driver_prompt.md) for the orchestration prompt.
