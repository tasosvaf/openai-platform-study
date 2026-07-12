#!/usr/bin/env python3
"""Run a list of QuixBugs Python tests against the (buggy) programs in ``python_programs/``.

This is the entry point for the experiment template. Every program under
``python_programs/`` contains a single-line defect; each test under
``python_testcases/`` exercises the matching program. Out of the box the tests
FAIL (that is the point) - an agent is expected to edit the buggy program until
its test passes.

Each program's tests run in their **own** pytest subprocess. That isolation
matters here: some buggy programs (e.g. ``bitcount``) loop forever, and a hang
in one program must not abort the rest of the run. Two independent guards stop a
hang: a per-test ``pytest-timeout`` (if installed) and a hard wall-clock timeout
enforced by this script.

Usage
-----
    python run_tests.py                     # run every test
    python run_tests.py bitcount gcd        # run only these programs' tests
    python run_tests.py bitcount --timeout 5
    python run_tests.py --list              # list the available test names
    python run_tests.py quicksort -k test_5 # extra args are passed through to pytest

Names may be given as ``bitcount``, ``test_bitcount`` or ``test_bitcount.py``.
``--runslow`` opts in to the one slow test case (``knapsack``).
Exit status is non-zero if any selected program's tests did not pass.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTDIR = ROOT / "python_testcases"
PREFIX = "test_"
SUFFIX = ".py"


def available_tests():
    """Return the sorted list of program names that have a test file."""
    return sorted(p.name[len(PREFIX):-len(SUFFIX)] for p in TESTDIR.glob("test_*.py"))


def normalize(name):
    """Accept bitcount / test_bitcount / test_bitcount.py -> bitcount."""
    if name.endswith(SUFFIX):
        name = name[:-len(SUFFIX)]
    if name.startswith(PREFIX):
        name = name[len(PREFIX):]
    return name


def has_timeout_plugin():
    try:
        import pytest_timeout  # noqa: F401
        return True
    except ImportError:
        return False


def run_one(name, per_test_timeout, wall_timeout, use_plugin, runslow, passthrough):
    """Run a single program's test file in its own pytest process.

    Returns ``(status, seconds, output)`` where status is one of
    ``pass`` / ``fail`` / ``timeout`` / ``error``.
    """
    target = str(TESTDIR / (PREFIX + name + SUFFIX))
    cmd = [sys.executable, "-m", "pytest", target, "-q"]
    if use_plugin and per_test_timeout:
        cmd.append("--timeout=" + str(per_test_timeout))
    if runslow:
        cmd.append("--runslow")
    cmd += passthrough

    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=wall_timeout,
            text=True,
        )
        elapsed = time.time() - start
        out = proc.stdout or ""
        if "Timeout +++" in out:
            status = "timeout"
        elif proc.returncode == 0:
            status = "pass"
        elif proc.returncode == 1:
            status = "fail"
        else:
            status = "error"
    except subprocess.TimeoutExpired as exc:
        elapsed = time.time() - start
        out = exc.stdout if isinstance(exc.stdout, str) else ""
        out += "\n[run_tests] wall-clock timeout after {:.0f}s - process killed.".format(
            wall_timeout
        )
        status = "timeout"

    return status, elapsed, out


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run a list of QuixBugs Python tests (each in its own process).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "tests",
        nargs="*",
        help="Program names to test (default: all). e.g. bitcount gcd quicksort",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Per-test timeout in seconds (requires pytest-timeout). 0 disables it. Default: 10.",
    )
    parser.add_argument(
        "--wall-timeout",
        type=int,
        default=120,
        help="Hard per-program wall-clock timeout in seconds (always enforced). Default: 120.",
    )
    parser.add_argument(
        "--runslow",
        action="store_true",
        help="Include the slow knapsack test case.",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only print the per-program result line, not each pytest report.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the available test names and exit.",
    )
    args, passthrough = parser.parse_known_args(argv)

    all_tests = available_tests()

    if args.list:
        print("\n".join(all_tests))
        return 0

    if args.tests:
        targets, unknown = [], []
        for raw in args.tests:
            name = normalize(raw)
            if name in all_tests:
                targets.append(name)
            else:
                unknown.append(raw)
        if unknown:
            parser.error(
                "unknown test(s): {}. Use --list to see the {} available names.".format(
                    ", ".join(unknown), len(all_tests)
                )
            )
    else:
        targets = all_tests

    use_plugin = has_timeout_plugin()
    if args.timeout and not use_plugin:
        print(
            "[run_tests] pytest-timeout not installed; relying on the wall-clock "
            "timeout only. Install it with 'pip install pytest-timeout' for a "
            "cleaner per-test timeout.",
            file=sys.stderr,
        )

    label = {"pass": "PASS", "fail": "FAIL", "timeout": "TIMEOUT", "error": "ERROR"}
    results = {}
    for name in targets:
        status, elapsed, out = run_one(
            name, args.timeout, args.wall_timeout, use_plugin, args.runslow, passthrough
        )
        results[name] = status
        if args.quiet:
            print("{:<28} {:>7}  ({:.1f}s)".format(name, label[status], elapsed))
        else:
            print("=" * 70)
            print("### {}  ->  {} ({:.1f}s)".format(name, label[status], elapsed))
            print("=" * 70)
            print(out.rstrip())

    counts = {k: 0 for k in label}
    for st in results.values():
        counts[st] += 1
    print("\n" + "-" * 70)
    print(
        "Summary: {} passed, {} failed, {} timeout, {} error  (of {})".format(
            counts["pass"], counts["fail"], counts["timeout"], counts["error"], len(targets)
        )
    )
    not_passed = sorted(n for n, st in results.items() if st != "pass")
    if not_passed:
        print("Not passing: " + ", ".join(not_passed))
    print("-" * 70)

    return 0 if not not_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
