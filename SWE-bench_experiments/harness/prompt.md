# General prompt — SWE-bench 3-instance run

Paste the block below into any of the six apps (GitHub Copilot CLI, VS Code
Copilot CLI, Cline, Aider, OpenAI Codex CLI, OpenAI Codex UI). It targets the same
three SWE-bench Lite instances so every tool solves the same task and results stay
comparable.

> Start a **fresh session** so the token count begins at zero when you ask the
> model to resolve it (see "Measuring session tokens" below).

---

## The prompt (copy from here)

```text
You are resolving three SWE-bench Lite issues. For EACH instance below, produce a
minimal unified-diff patch that fixes the issue in the target repository, then
place it in predictions/<level>.jsonl as the "model_patch" field (keep the same
instance_id; set model_name_or_path to the model you are).

  - easy   -> instance matplotlib__matplotlib-23563  (repo: matplotlib)
             'Line3D' object has no attribute '_verts3d'
  - medium -> instance sympy__sympy-22005            (repo: sympy)
             detection of infinite solution request
  - hard   -> instance django__django-11019          (repo: django)
             Merging 3+ media objects throws unnecessary MediaOrderConflictWarnings

For each instance:
  1. State the ROOT CAUSE in one or two sentences and cite the file(s) and, if you
     can, the exact lines you are changing.
  2. Produce the smallest correct patch (unified diff, `a/`…`b/` paths).
  3. Write it into predictions/<level>.jsonl (one JSON object per line).

Rules:
  - Keep patches minimal and targeted; do not reformat unrelated code.
  - Do NOT edit the test files the grader uses.
  - If you are unsure of the root cause, say so and ask rather than guessing.

Do not run Docker yourself. When all three patches are written, tell me you are
done and I will run the SWE-bench evaluation (./run_experiment.sh) and collect the
results.
```

(End of prompt.)

---

## Measuring session tokens (before → after)

1. **Start a fresh session** → `tokens_before = 0` (or read the counter first and
   use that).
2. **Paste the prompt** and let the agent produce all three patches.
3. **Read the session token total** (`tokens_after`):
   - GitHub Copilot CLI / VS Code Copilot CLI — `/usage`.
   - Cline — the task header (tokens in/out + cost).
   - Aider — `/tokens` (start with `--cost` for live cost).
   - OpenAI Codex CLI — `/status`.
   - OpenAI Codex UI — the usage panel.
4. **Run + collect**, recording the numbers:

   ```bash
   ./run_experiment.sh all 2 --local        # produce the SWE-bench reports
   python3 harness/swe_experiment_runner.py evaluate \
       --tool <tool> --model <model> \
       --tokens-before 0 --tokens-after <after> --cost-usd <cost>
   ```

Then compare across apps:

```bash
python3 harness/swe_experiment_runner.py compare
```
