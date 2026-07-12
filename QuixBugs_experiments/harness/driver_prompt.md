# Driver prompt (paste this to run a full experiment)

```text
Before doing anything, ask me three things and wait for my answers:
  1. Which tool are we testing? Reply with the NUMBER:
       1) github_copilot_cli   — GitHub Copilot CLI
       2) vscode_copilot_cli   — VS Code Copilot CLI
       3) cline                — Cline
       4) aider                — Aider
       5) openai_codex_cli      — OpenAI Codex CLI
       6) openai_codex_ui       — OpenAI Codex UI
  2. What is the model name? (default: GPT 5.4-mini)
  3. What output folder should the results go in?
     (default: /Users/tasosvaf/repos/testRepos/experiment_results/QuixBugs_results)

Then read harness/prompt.md and follow it exactly: fix ONLY the single-line bug in
each of python_programs/sieve.py, next_permutation.py and shortest_path_lengths.py,
verifying each with `python3 run_tests.py <name>`. Do not touch any other file.

When all three pass, STOP and ask me to read the session token usage from the tool
and give you: tokens-before, tokens-after, and cost in USD. Wait for my reply.

After I give you those numbers, generate the result document by running:

  python3 harness/experiment_runner.py evaluate \
      --tool <tool> --model "<model>" \
      --results-dir "<output folder>" \
      --tokens-before <before> --tokens-after <after> --cost-usd <cost>

Finally, show me where the results were written.
```
