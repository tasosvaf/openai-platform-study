# Driver prompt (paste this to run a full experiment)

```text
Before doing anything, ask me three things and wait for my answers:
  1. Which tool are we testing? (one of: github_copilot_cli, vscode_copilot_cli,
     cline, aider, openai_codex_cli, openai_codex_ui)
  2. What is the model name?
  3. What output folder should the results go in?

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
