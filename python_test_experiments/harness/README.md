# QuixBugs agent-comparison harness

Run the **same** 40-program QuixBugs Python benchmark against different coding
agents / platforms and export a comparable result set for each one:

- GitHub Copilot CLI
- VS Code Copilot CLI
- Cline
- Aider
- OpenAI Codex CLI
- OpenAI Codex UI

Everything the harness produces goes to a **results folder** (created if it does
not exist). Default:

```
/Users/tasosvaf/repos/testRepos/experiment_results/QuixBugs_python_results
```

Override per command with `--results-dir <path>`.

---

## What gets measured

For every run the harness records automatically:

- **Fixed correctly** — how many of the evaluated programs now pass their tests
  (the default run evaluates 3 programs; `--full` evaluates all 40).
- **Fix rate** — fixed / total.
- **Programs edited** — how many files the agent actually touched.
- **Per-program status** — pass / fail / timeout / error + wall-clock time.
- **Diffs** — a unified diff per edited program, under `diffs/<name>.diff`
  (this is the "diff path on how they were fixed").
- **Token cost** — `tokens_before`, `tokens_after`, `tokens_used`, `cost_usd`
  (you supply the before/after numbers; the harness stores the delta).

You fill in the **qualitative rubric** (`scorecard.md`) after inspecting the run:

| Criterion | What you observe |
| --- | --- |
| Diagnosis quality | Did it find the true / likely root cause? |
| Evidence use | Did it cite specific files, lines, logs, or docs? |
| Hallucination risk | Did it invent APIs, files, or assumptions? |
| Missing-context behavior | Did it ask useful clarifying questions? |
| Fix quality | Was the proposed fix safe and minimal? |
| Test quality | Did it propose a meaningful regression test? |
| Platform insight | What does this reveal about the agent platform? |

---

## One-time setup

```bash
cd /Users/tasosvaf/repos/testRepos/openai-platform-study/python_test_experiments
pip install pytest pytest-timeout

# Capture the pristine buggy baseline (used for diffs and reset). Do this ONCE,
# before any agent touches the programs.
python harness/experiment_runner.py snapshot
```

---

## Default run vs full run

By default `evaluate` runs a **3-program set** — one easy, one medium, one hard —
chosen so a quick pass still exercises the full range of diagnosis difficulty:

| Tier | Program | The single-line bug | Why it was picked |
| --- | --- | --- | --- |
| easy | `sieve` | `any(n % p > 0 …)` → `all(…)` | Well-known algorithm, fast/deterministic, clean logic inversion |
| medium | `next_permutation` | `perm[j] < perm[i]` → `perm[j] > perm[i]` | Real algorithm; must know to swap with the smallest element greater than `perm[i]` |
| hard | `shortest_path_lengths` | `length_by_path[j, k]` → `length_by_path[k, j]` | Floyd–Warshall index transposition; rewards real reasoning, punishes hallucination |

Scope flags:

```bash
python harness/experiment_runner.py evaluate --tool aider              # default: the 3 above
python harness/experiment_runner.py evaluate --tool aider --full       # all 40 programs
python harness/experiment_runner.py evaluate --tool aider --only gcd sieve   # a custom subset
```

The result artifacts are identical in every scope; only the number of programs
evaluated changes. `summary.json` records the `scope` and each program's tier.

**One prompt for all six apps:** paste the block in [`prompt.md`](prompt.md) into
any tool — it targets exactly these three programs so every app solves the same
task. It also explains how to bracket the session token count (start a fresh
session → `tokens_before = 0`, read the tool's usage counter afterward →
`tokens_after`).

---

## The loop for each tool

```bash
# 1. Start from a clean, fully-buggy tree.
python harness/experiment_runner.py reset

# 2. Run the agent so it edits files in python_programs/ (see per-tool commands
#    below). Note the session's token count before and after.

# 3. Evaluate + export the run.
python harness/experiment_runner.py evaluate \
    --tool aider \
    --model gpt-5.1 \
    --tokens-before 0 \
    --tokens-after 152340 \
    --cost-usd 0.34 \
    --notes "single pass, no clarifying questions"
```

Results land in `<results-dir>/aider/run_<timestamp>/`.

Compare everything recorded so far:

```bash
python harness/experiment_runner.py compare
```

---

## Per-tool example commands

Run all of these **from the benchmark folder** so `conftest.py` and the
`python_programs` package resolve. Point each agent at the buggy files and this
task: *"Each file in `python_programs/` has a single-line bug. Fix the bug so the
matching test in `python_testcases/` passes. Do not edit the tests."*

The suggested prompt (reuse for every tool):

```
The folder python_programs/ contains 40 Python programs, each with a single-line
defect. The matching tests are in python_testcases/. Run
`python run_tests.py <name>` to see a failure, fix ONLY the buggy line in
python_programs/<name>.py, and re-run until it passes. Do not modify any test,
JSON data, or other file.
```

### GitHub Copilot CLI

```bash
# Interactive session in the repo:
copilot
# then paste the prompt above.

# Or one-shot:
copilot -p "Fix the single-line bug in each file under python_programs/ so the tests in python_testcases/ pass. Do not edit tests." --allow-all-tools
```
Token usage: run `/usage` inside the session (or check the end-of-session
summary) for the before/after token counts.

### VS Code Copilot CLI

```bash
# The VS Code build of the Copilot CLI:
code copilot            # or: code-insiders copilot
# paste the prompt above.
```
Token usage: use the session `/usage` command or the Copilot usage panel.

### Cline

Cline runs inside VS Code. Open this folder in VS Code, open the Cline panel,
select the model, and paste the prompt above. Cline reports **tokens in/out and
cost** in its task header — read the totals before starting and after finishing.

### Aider

```bash
aider --model gpt-5.1 python_programs/*.py
# then paste the prompt above, or drive one file at a time:
aider --model gpt-5.1 python_programs/gcd.py
```
Token usage: Aider prints tokens **and cost** after each exchange; run `/tokens`
for the session total, or start with `--cost` to see per-message cost.

### OpenAI Codex CLI

```bash
codex "Fix the single-line bug in each file under python_programs/ so the tests in python_testcases/ pass. Do not edit tests."
# or interactive:
codex
```
Token usage: run `/status` inside the session for the token counter, or read the
end-of-turn usage line.

### OpenAI Codex UI

Use the Codex web/IDE UI. Connect it to this repository, paste the prompt above,
and let it apply the edits (or apply the produced patch locally). Read the token
usage from the Codex UI's usage panel for the before/after numbers.

> After the agent finishes in the UI, make sure the edited `python_programs/`
> files are present locally, then run the `evaluate` command with
> `--tool openai_codex_ui`.

---

## Output layout

```
<results-dir>/
├── README.md                     # auto leaderboard (latest run per tool)
├── github_copilot_cli/
│   ├── index.md                  # all runs for this tool
│   └── run_20260712_101500/
│       ├── summary.json          # machine-readable everything
│       ├── summary.md            # human summary + per-program table
│       ├── scorecard.md          # qualitative rubric to fill in
│       ├── tokens.json           # before / after / used / cost
│       ├── test_output.txt       # full pytest output per program
│       └── diffs/
│           ├── gcd.diff          # how each program was fixed
│           └── ...
├── vscode_copilot_cli/
├── cline/
├── aider/
├── openai_codex_cli/
└── openai_codex_ui/
```

## Notes

- `snapshot` stores the pristine files in `harness/baseline/`. `reset` restores
  them. Re-snapshot only if the upstream buggy programs change (`snapshot --force`).
- Token counts are supplied by you because each tool reports them differently;
  the harness records the delta and cost verbatim so runs stay comparable.
- `knapsack` has one very slow test case, skipped unless you pass `--runslow`.
