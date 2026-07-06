# QuixBugs Python Test Experiments

A **self-contained, answer-free** template for running the 40 Python programs from the
[QuixBugs](https://github.com/jkoppel/QuixBugs) benchmark against their test suites.

Every program in [`python_programs/`](python_programs) contains a **single-line defect**, and
each test in [`python_testcases/`](python_testcases) exercises the matching program. Out of the
box the tests **fail on purpose** — this folder is meant to be handed to an agent (or a human)
whose job is to **edit the buggy program until its test passes**.

> This template deliberately contains **no corrected/reference versions** of the programs and no
> hints about the fixes. It is a clean starting point you can point different agents at and then
> measure how many bugs each one repairs.

## Layout

```
python_test_experiments/
├── README.md                 # this file
├── run_tests.py              # run a list of tests (see below)
├── conftest.py               # adds the --runslow pytest option
├── python_programs/          # 40 buggy programs — THIS is what you fix
├── python_testcases/         # 40 pytest files + load_testdata.py + node.py
└── json_testcases/           # input/expected data for the non-graph tests
```

These are the minimum files required to run the Python tests; nothing else from the upstream
repository is needed.

## Setup

```bash
pip install pytest pytest-timeout
```

`pytest-timeout` is optional but strongly recommended: some buggy programs (e.g. `bitcount`)
loop forever, and the timeout stops a single defect from hanging the whole run.

## Running the tests

Use the helper script (recommended — it applies a per-test timeout by default):

```bash
python run_tests.py                 # run every test
python run_tests.py bitcount gcd    # run only these programs' tests
python run_tests.py --list          # list the available test names
python run_tests.py quicksort -k test_5   # extra args pass straight through to pytest
python run_tests.py --timeout 5     # change / disable (0) the per-test timeout
python run_tests.py knapsack --runslow    # include the one slow test case
```

Or call `pytest` directly from this folder:

```bash
pytest                                        # all tests (add --timeout=10 to avoid hangs)
pytest python_testcases/test_quicksort.py     # a single program
pytest --timeout=10 python_testcases          # whole suite with a safety timeout
```

## The experiment loop

1. Pick a program, e.g. `gcd`. Run `python run_tests.py gcd` — the test fails.
2. Give the agent `python_programs/gcd.py` and the failing test output.
3. The agent edits **only** `python_programs/gcd.py` to fix the one-line defect.
4. Re-run `python run_tests.py gcd`. When it passes, the bug is fixed.

Because each defect is a single line, a repair should never require touching the tests, the data,
or any other file. If a "fix" needs to change a test, it is not a valid repair.

## Notes / gotchas

- **Timeouts.** `bitcount` (and a couple of others) can loop forever in their buggy state. Always
  run with a timeout (the default via `run_tests.py`, or `--timeout=N` with `pytest`).
- **Slow case.** `knapsack` has one test case that takes minutes to pass even when correct; it is
  skipped unless you pass `--runslow`.
- **Graph programs.** `breadth_first_search`, `depth_first_search`, `detect_cycle`,
  `minimum_spanning_tree`, `reverse_linked_list`, `shortest_path_length`, `shortest_path_lengths`,
  `shortest_paths`, and `topological_ordering` build their inputs in Python (via `node.py`) instead
  of loading JSON, so they have no file in `json_testcases/`.
- **Imports.** Tests import the program under test as `from python_programs.<name> import <name>`.
  Running from this folder (so `conftest.py` is picked up) makes that resolve correctly.

## The 40 programs

`bitcount`, `breadth_first_search`, `bucketsort`, `depth_first_search`, `detect_cycle`,
`find_first_in_sorted`, `find_in_sorted`, `flatten`, `gcd`, `get_factors`, `hanoi`,
`is_valid_parenthesization`, `kheapsort`, `knapsack`, `kth`, `lcs_length`, `levenshtein`, `lis`,
`longest_common_subsequence`, `max_sublist_sum`, `mergesort`, `minimum_spanning_tree`,
`next_palindrome`, `next_permutation`, `pascal`, `possible_change`, `powerset`, `quicksort`,
`reverse_linked_list`, `rpn_eval`, `shortest_path_length`, `shortest_path_lengths`,
`shortest_paths`, `shunting_yard`, `sieve`, `sqrt`, `subsequences`, `to_base`,
`topological_ordering`, `wrap`.
