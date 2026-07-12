# Driver prompt (paste this to run a full SWE-bench experiment)

```text
Before doing anything, ask me three things and wait for my answers:
  1. Which tool are we testing? Reply with the NUMBER:
       1) github_copilot_cli   — GitHub Copilot CLI
       2) vscode_copilot_cli   — VS Code Copilot CLI
       3) cline                — Cline
       4) aider                — Aider
       5) openai_codex_cli      — OpenAI Codex CLI
       6) openai_codex_ui       — OpenAI Codex UI
  2. What is the model name? (default: GPT 5.4-mini; must match model_name_or_path
     in the predictions)
  3. What output folder should the results go in?
     (default: /Users/tasosvaf/repos/testRepos/experiment_results/SWE-bench_results)

Then read harness/prompt.md and follow it exactly: produce a minimal unified-diff
patch for each of the three instances (matplotlib__matplotlib-23563,
sympy__sympy-22005, django__django-11019) and write each into
predictions/<level>.jsonl as model_patch. Do NOT run Docker.

When all three patches are written, STOP and tell me. I will run
`./run_experiment.sh all 2 --local` to evaluate them in Docker, then read the
session token usage from the tool and give you: tokens-before, tokens-after, and
cost in USD. Wait for my reply.

After I confirm the evaluation is done and give you those numbers, collect and
export the result document by running:

  python3 harness/swe_experiment_runner.py evaluate \
      --tool <tool> --model "<model>" \
      --results-dir "<output folder>" \
      --tokens-before <before> --tokens-after <after> --cost-usd <cost>

Finally, show me where the results were written.
```
