# General prompt — default 3-program run

Paste the block below into **any** of the apps (GitHub Copilot CLI, VS Code
Copilot CLI, Cline, Aider, OpenAI Codex CLI, OpenAI Codex UI). It targets exactly
the default easy/medium/hard set that `evaluate` checks, so every tool solves the
same task and the results stay comparable.

> Start a **fresh session** before pasting, so the token count begins at zero when
> you ask the model to resolve it (see "Measuring session tokens" below).

---

## The prompt (copy from here)

```text
You are fixing bugs in the QuixBugs Python benchmark. Work inside the repository
folder `QuixBugs_experiments/`.

Each of these THREE files contains exactly ONE single-line defect:

  1. python_programs/sieve.py
  2. python_programs/next_permutation.py
  3. python_programs/shortest_path_lengths.py

The matching tests are python_testcases/test_sieve.py,
test_next_permutation.py and test_shortest_path_lengths.py, with input/expected
data in json_testcases/.

For EACH of the three programs, in order:
  1. Run its test to see the failure:  python3 run_tests.py <name>
  2. State the ROOT CAUSE in one sentence and cite the exact file and line number
     of the buggy line.
  3. Fix ONLY that single line in python_programs/<name>.py.
  4. Re-run  python3 run_tests.py <name>  and confirm it now passes.

Hard rules:
  - Change only the one buggy line per file. Do not rewrite functions or logic.
  - Do NOT edit any test file, any JSON data file, or any other file.
  - Do NOT add new files, imports, or dependencies.
  - If you are unsure of the root cause, say so and ask, rather than guessing.

When all three are fixed, verify together and report the result:
  python3 run_tests.py sieve next_permutation shortest_path_lengths
```

(End of prompt.)

---

## Notes for specific apps

- **Codex UI / any tool that can't run shell commands here:** it should still
  produce the three one-line edits. Apply them locally, then run the verify command
  yourself.
- **`python` vs `python3`:** this machine only has `python3`. If a tool insists on
  `python`, tell it to use `python3` (or add a shim).

---

## Measuring session tokens (before → after)

You want to measure tokens "from when I ask the model to resolve it", so bracket
the paste:

1. **Start a fresh session.** With an empty session the count starts at 0, so
   `tokens_before = 0`. (If you reuse a session, read the counter first and use
   that as `tokens_before`.)
2. **Paste the prompt** and let the agent finish all three fixes.
3. **Read the session token total** (`tokens_after`). Where to read it:
   - GitHub Copilot CLI / VS Code Copilot CLI — `/usage` in the session.
   - Cline — the tokens in/out + cost shown in the task header.
   - Aider — `/tokens` for the session total (start with `--cost` for live cost).
   - OpenAI Codex CLI — `/status` for the token counter.
   - OpenAI Codex UI — the usage panel for that conversation.
4. **Record it on the run:**

   ```bash
   python3 harness/experiment_runner.py evaluate \
       --tool <tool> --model <model> \
       --tokens-before 0 --tokens-after <after> --cost-usd <cost>
   ```

   The harness stores `tokens_used = after - before` in `tokens.json` and every
   summary. (No `--full` / `--only` means it evaluates exactly these three.)

Run the same prompt in each app, then compare:

```bash
python3 harness/experiment_runner.py compare
```
