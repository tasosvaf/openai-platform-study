#!/usr/bin/env python3
"""Experiment harness for the QuixBugs Python benchmark.

Run the *same* benchmark against different coding agents / platforms
(GitHub Copilot CLI, VS Code Copilot CLI, Cline, Aider, OpenAI Codex CLI,
OpenAI Codex UI, ...) and export a comparable set of results for each run.

Workflow
--------
1. Capture the pristine (buggy) baseline once::

       python harness/experiment_runner.py snapshot

2. Before letting an agent loose, reset the programs to the baseline::

       python harness/experiment_runner.py reset

3. Let the agent fix the bugs in ``python_programs/`` (see harness/README.md
   for per-tool example commands).

4. Evaluate + export the run::

       python harness/experiment_runner.py evaluate \
           --tool aider \
           --tokens-before 0 --tokens-after 152340 --cost-usd 0.34

5. Compare every recorded run::

       python harness/experiment_runner.py compare

Each ``evaluate`` writes, under the results directory, one folder per run
containing: a machine-readable ``summary.json``, a human ``summary.md``, a
``scorecard.md`` (the qualitative rubric to fill in), the full ``test_output.txt``,
a ``tokens.json`` and per-program unified diffs under ``diffs/``.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
ROOT = HARNESS_DIR.parent
PROGRAMS_DIR = ROOT / "python_programs"
BASELINE_DIR = HARNESS_DIR / "baseline"

# Base results folder shared by both benchmarks; each benchmark writes into its
# own subfolder beneath it.
EXPERIMENT_RESULTS_ROOT = Path("/Users/tasosvaf/repos/testRepos/experiment_results")
DEFAULT_RESULTS_DIR = EXPERIMENT_RESULTS_ROOT / "QuixBugs_results"

# Default model recorded on a run unless overridden with --model.
DEFAULT_MODEL = "GPT 5.4-mini"

# slug -> human readable display name. The slug is the folder name on disk.
TOOLS = {
    "github_copilot_cli": "GitHub Copilot CLI",
    "vscode_copilot_cli": "VS Code Copilot CLI",
    "cline": "Cline",
    "aider": "Aider",
    "openai_codex_cli": "OpenAI Codex CLI",
    "openai_codex_ui": "OpenAI Codex UI",
}

# The default ("quick") benchmark: one easy, one medium, one hard program.
# A default `evaluate` run checks just these three; `--full` runs all 40.
#   - sieve:                 easy   (any -> all logic inversion, fast/deterministic)
#   - next_permutation:      medium (comparison flip inside a real algorithm)
#   - shortest_path_lengths: hard   (Floyd-Warshall index transposition)
DEFAULT_PROGRAMS = [
    ("sieve", "easy"),
    ("next_permutation", "medium"),
    ("shortest_path_lengths", "hard"),
]

# The qualitative rubric the user asked to observe for every run.
RUBRIC = [
    ("Diagnosis quality", "Did it find the true / likely root cause?"),
    ("Evidence use", "Did it cite specific files, lines, logs, or docs?"),
    ("Hallucination risk", "Did it invent APIs, files, or assumptions?"),
    ("Missing-context behavior", "Did it ask useful clarifying questions?"),
    ("Fix quality", "Was the proposed fix safe and minimal?"),
    ("Test quality", "Did it propose a meaningful regression test?"),
    ("Platform insight", "What does this reveal about the agent platform?"),
]


# --------------------------------------------------------------------------- #
# Load run_tests.py (sibling of this harness dir) as a module so we can reuse
# its per-program, timeout-guarded test runner instead of reimplementing it.
# --------------------------------------------------------------------------- #
def _load_run_tests():
    spec = importlib.util.spec_from_file_location("run_tests", ROOT / "run_tests.py")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT))  # so 'python_programs' / conftest resolve
    spec.loader.exec_module(module)
    return module


def _program_files():
    return sorted(PROGRAMS_DIR.glob("*.py"))


def _timestamp():
    return _dt.datetime.now().strftime("%Y%m%d_%H%M%S")


# --------------------------------------------------------------------------- #
# snapshot / reset
# --------------------------------------------------------------------------- #
def cmd_snapshot(args):
    """Copy the current (buggy) programs into harness/baseline/."""
    if BASELINE_DIR.exists() and not args.force:
        print(
            f"[snapshot] baseline already exists at {BASELINE_DIR}. "
            "Re-run with --force to overwrite."
        )
        return 1
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    for src in _program_files():
        shutil.copy2(src, BASELINE_DIR / src.name)
        n += 1
    print(f"[snapshot] captured {n} pristine programs -> {BASELINE_DIR}")
    return 0


def cmd_reset(args):
    """Restore python_programs/ from the captured baseline."""
    if not BASELINE_DIR.exists():
        print("[reset] no baseline found. Run 'snapshot' first.", file=sys.stderr)
        return 1
    n = 0
    for src in sorted(BASELINE_DIR.glob("*.py")):
        shutil.copy2(src, PROGRAMS_DIR / src.name)
        n += 1
    print(f"[reset] restored {n} programs from baseline.")
    return 0


# --------------------------------------------------------------------------- #
# diffs
# --------------------------------------------------------------------------- #
def _diff_for(name):
    """Return (changed, unified_diff_text) for one program vs the baseline."""
    cur = PROGRAMS_DIR / f"{name}.py"
    base = BASELINE_DIR / f"{name}.py"
    cur_lines = cur.read_text().splitlines(keepends=True) if cur.exists() else []
    base_lines = base.read_text().splitlines(keepends=True) if base.exists() else []
    diff = list(
        difflib.unified_diff(
            base_lines, cur_lines,
            fromfile=f"baseline/{name}.py",
            tofile=f"python_programs/{name}.py",
        )
    )
    return bool(diff), "".join(diff)


# --------------------------------------------------------------------------- #
# evaluate
# --------------------------------------------------------------------------- #
def cmd_evaluate(args):
    if not BASELINE_DIR.exists():
        print(
            "[evaluate] no baseline found. Run 'snapshot' before your first "
            "experiment so diffs and 'fixed' counts are meaningful.",
            file=sys.stderr,
        )
        return 1

    run_tests = _load_run_tests()
    tool_slug = args.tool
    tool_name = TOOLS[tool_slug]

    results_dir = Path(args.results_dir).expanduser()
    label = args.label or _timestamp()
    run_dir = results_dir / tool_slug / f"run_{label}"
    diffs_dir = run_dir / "diffs"
    diffs_dir.mkdir(parents=True, exist_ok=True)

    use_plugin = run_tests.has_timeout_plugin()
    all_tests = run_tests.available_tests()
    difficulty_by_name = dict(DEFAULT_PROGRAMS)

    if args.only:
        unknown = [n for n in args.only if n not in all_tests]
        if unknown:
            print(
                f"[evaluate] unknown program(s): {', '.join(unknown)}. "
                f"Use 'python run_tests.py --list' to see valid names.",
                file=sys.stderr,
            )
            return 1
        targets = list(args.only)
        scope = "custom"
    elif args.full:
        targets = all_tests
        scope = "full"
    else:
        targets = [n for n, _ in DEFAULT_PROGRAMS]
        scope = "default"

    print(
        f"[evaluate] {tool_name}: scope={scope}, "
        f"running {len(targets)} program test suite(s)..."
    )

    per_program = {}
    full_output_chunks = []
    counts = {"pass": 0, "fail": 0, "timeout": 0, "error": 0}

    for name in targets:
        status, elapsed, out = run_tests.run_one(
            name,
            per_test_timeout=args.timeout,
            wall_timeout=args.wall_timeout,
            use_plugin=use_plugin,
            runslow=args.runslow,
            passthrough=[],
        )
        counts[status] = counts.get(status, 0) + 1
        changed, diff_text = _diff_for(name)
        diff_path = None
        if changed:
            diff_path = diffs_dir / f"{name}.diff"
            diff_path.write_text(diff_text)

        difficulty = difficulty_by_name.get(name)
        per_program[name] = {
            "status": status,
            "difficulty": difficulty,
            "seconds": round(elapsed, 2),
            "changed": changed,
            "diff": (str(diff_path.relative_to(run_dir)) if diff_path else None),
        }
        full_output_chunks.append(
            "=" * 70
            + f"\n### {name} -> {status.upper()} ({elapsed:.1f}s)"
            + ("  [edited]" if changed else "  [unchanged]")
            + "\n" + "=" * 70 + "\n" + out.rstrip() + "\n"
        )
        tag = f" [{difficulty}]" if difficulty else ""
        print(
            f"  {name:<28}{tag:<10} {status.upper():>7} "
            f"({elapsed:4.1f}s){'  edited' if changed else ''}"
        )

    total = len(targets)
    fixed = counts["pass"]
    edited = sum(1 for p in per_program.values() if p["changed"])

    # token / cost accounting -------------------------------------------------
    tokens_before = args.tokens_before
    tokens_after = args.tokens_after
    tokens_delta = None
    if tokens_before is not None and tokens_after is not None:
        tokens_delta = tokens_after - tokens_before
    tokens = {
        "tokens_before": tokens_before,
        "tokens_after": tokens_after,
        "tokens_used": tokens_delta,
        "cost_usd": args.cost_usd,
        "model": args.model,
    }
    (run_dir / "tokens.json").write_text(json.dumps(tokens, indent=2) + "\n")

    # summary.json ------------------------------------------------------------
    summary = {
        "tool_slug": tool_slug,
        "tool_name": tool_name,
        "model": args.model,
        "label": label,
        "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
        "scope": scope,
        "total_programs": total,
        "fixed_correctly": fixed,
        "fix_rate": round(fixed / total, 4) if total else 0.0,
        "programs_edited": edited,
        "counts": counts,
        "tokens": tokens,
        "notes": args.notes,
        "per_program": per_program,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (run_dir / "test_output.txt").write_text("\n".join(full_output_chunks))

    _write_summary_md(run_dir, summary)
    _write_scorecard_md(run_dir, summary)
    _write_tool_index(results_dir, tool_slug)
    _write_top_readme(results_dir)

    print("\n" + "-" * 70)
    print(
        f"[evaluate] {tool_name}: {fixed}/{total} fixed correctly "
        f"({summary['fix_rate'] * 100:.1f}%), {edited} programs edited."
    )
    if tokens_delta is not None:
        print(f"[evaluate] tokens used: {tokens_delta:,}"
              + (f"  (~${args.cost_usd})" if args.cost_usd is not None else ""))
    print(f"[evaluate] results -> {run_dir}")
    print(f"[evaluate] fill in the qualitative rubric: {run_dir / 'scorecard.md'}")
    return 0


def _write_summary_md(run_dir: Path, s: dict):
    lines = [
        f"# {s['tool_name']} — run `{s['label']}`",
        "",
        f"- **Timestamp:** {s['timestamp']}",
        f"- **Model:** {s['model'] or '_(unspecified)_'}",
        f"- **Scope:** {s.get('scope', 'full')} ({s['total_programs']} programs)",
        f"- **Fixed correctly:** {s['fixed_correctly']} / {s['total_programs']} "
        f"({s['fix_rate'] * 100:.1f}%)",
        f"- **Programs edited:** {s['programs_edited']}",
        f"- **Pass / Fail / Timeout / Error:** "
        f"{s['counts']['pass']} / {s['counts']['fail']} / "
        f"{s['counts']['timeout']} / {s['counts']['error']}",
    ]
    t = s["tokens"]
    if t["tokens_used"] is not None:
        lines.append(
            f"- **Tokens used:** {t['tokens_used']:,} "
            f"(before {t['tokens_before']:,} → after {t['tokens_after']:,})"
        )
    if t["cost_usd"] is not None:
        lines.append(f"- **Cost:** ${t['cost_usd']}")
    if s["notes"]:
        lines += ["", f"> {s['notes']}"]

    lines += [
        "",
        "## Per-program results",
        "",
        "| Program | Difficulty | Result | Time (s) | Edited | Diff |",
        "| --- | --- | --- | ---: | :---: | --- |",
    ]
    for name, p in s["per_program"].items():
        diff = f"[diff]({p['diff']})" if p["diff"] else "—"
        edited = "✓" if p["changed"] else ""
        difficulty = p.get("difficulty") or "—"
        lines.append(
            f"| {name} | {difficulty} | {p['status'].upper()} | "
            f"{p['seconds']:.1f} | {edited} | {diff} |"
        )
    lines.append("")
    (run_dir / "summary.md").write_text("\n".join(lines))


def _write_scorecard_md(run_dir: Path, s: dict):
    scorecard = run_dir / "scorecard.md"
    if scorecard.exists():
        return  # never clobber a rubric the user has already filled in
    lines = [
        f"# Qualitative scorecard — {s['tool_name']} (run `{s['label']}`)",
        "",
        "Fill this in after inspecting the run. Score each criterion 1–5 and add",
        "evidence (file/line references, quotes from the agent transcript).",
        "",
        "| Criterion | What you observe | Score (1–5) | Evidence / notes |",
        "| --- | --- | :---: | --- |",
    ]
    for crit, observe in RUBRIC:
        lines.append(f"| {crit} | {observe} |  |  |")
    lines += [
        "",
        "## Quantitative summary (auto-filled)",
        "",
        f"- Fixed correctly: **{s['fixed_correctly']} / {s['total_programs']}** "
        f"({s['fix_rate'] * 100:.1f}%)",
        f"- Programs edited: {s['programs_edited']}",
    ]
    t = s["tokens"]
    if t["tokens_used"] is not None:
        lines.append(f"- Tokens used: {t['tokens_used']:,}")
    if t["cost_usd"] is not None:
        lines.append(f"- Cost: ${t['cost_usd']}")
    lines += [
        "",
        "## Transcript / free-form observations",
        "",
        "_Paste key excerpts, clarifying questions asked, hallucinations, etc._",
        "",
    ]
    scorecard.write_text("\n".join(lines))


def _iter_runs(tool_dir: Path):
    if not tool_dir.exists():
        return
    for run_dir in sorted(tool_dir.glob("run_*")):
        sj = run_dir / "summary.json"
        if sj.exists():
            try:
                yield run_dir, json.loads(sj.read_text())
            except json.JSONDecodeError:
                continue


def _write_tool_index(results_dir: Path, tool_slug: str):
    tool_dir = results_dir / tool_slug
    rows = ["| Run | Fixed | Rate | Tokens | Cost |", "| --- | ---: | ---: | ---: | ---: |"]
    for run_dir, s in _iter_runs(tool_dir):
        t = s.get("tokens", {})
        tok = f"{t['tokens_used']:,}" if t.get("tokens_used") is not None else "—"
        cost = f"${t['cost_usd']}" if t.get("cost_usd") is not None else "—"
        rows.append(
            f"| [{run_dir.name}]({run_dir.name}/summary.md) | "
            f"{s['fixed_correctly']}/{s['total_programs']} | "
            f"{s['fix_rate'] * 100:.1f}% | {tok} | {cost} |"
        )
    content = [f"# {TOOLS.get(tool_slug, tool_slug)} — runs", ""] + rows + [""]
    tool_dir.mkdir(parents=True, exist_ok=True)
    (tool_dir / "index.md").write_text("\n".join(content))


def _write_top_readme(results_dir: Path):
    lines = [
        "# QuixBugs Python — agent comparison results",
        "",
        "Auto-generated. Each subfolder is one agent/platform; each `run_*` is one",
        "evaluated experiment. See `harness/README.md` in the benchmark repo for how",
        "to reproduce a run.",
        "",
        "## Latest run per tool",
        "",
        "| Tool | Latest run | Fixed | Rate | Tokens | Cost |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for slug, name in TOOLS.items():
        runs = list(_iter_runs(results_dir / slug))
        if not runs:
            lines.append(f"| {name} | _no runs yet_ | — | — | — | — |")
            continue
        run_dir, s = runs[-1]
        t = s.get("tokens", {})
        tok = f"{t['tokens_used']:,}" if t.get("tokens_used") is not None else "—"
        cost = f"${t['cost_usd']}" if t.get("cost_usd") is not None else "—"
        lines.append(
            f"| {name} | [{run_dir.name}]({slug}/{run_dir.name}/summary.md) | "
            f"{s['fixed_correctly']}/{s['total_programs']} | "
            f"{s['fix_rate'] * 100:.1f}% | {tok} | {cost} |"
        )
    lines.append("")
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "README.md").write_text("\n".join(lines))


# --------------------------------------------------------------------------- #
# compare
# --------------------------------------------------------------------------- #
def cmd_compare(args):
    results_dir = Path(args.results_dir).expanduser()
    if not results_dir.exists():
        print(f"[compare] no results directory at {results_dir}", file=sys.stderr)
        return 1
    print(f"Results in {results_dir}\n")
    header = f"{'Tool':<24}{'Run':<20}{'Fixed':>8}{'Rate':>8}{'Tokens':>12}{'Cost':>10}"
    print(header)
    print("-" * len(header))
    any_run = False
    for slug, name in TOOLS.items():
        for run_dir, s in _iter_runs(results_dir / slug):
            any_run = True
            t = s.get("tokens", {})
            tok = f"{t['tokens_used']:,}" if t.get("tokens_used") is not None else "-"
            cost = f"${t['cost_usd']}" if t.get("cost_usd") is not None else "-"
            print(
                f"{name:<24}{s['label']:<20}"
                f"{s['fixed_correctly']}/{s['total_programs']:<6}"
                f"{s['fix_rate'] * 100:>6.1f}%{tok:>12}{cost:>10}"
            )
    if not any_run:
        print("(no evaluated runs yet)")
    _write_top_readme(results_dir)
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("snapshot", help="Capture the pristine buggy baseline.")
    sp.add_argument("--force", action="store_true", help="Overwrite an existing baseline.")
    sp.set_defaults(func=cmd_snapshot)

    rp = sub.add_parser("reset", help="Restore python_programs/ from the baseline.")
    rp.set_defaults(func=cmd_reset)

    ep = sub.add_parser("evaluate", help="Run the tests and export a result set.")
    ep.add_argument("--tool", required=True, choices=sorted(TOOLS), help="Agent/platform.")
    default_names = ", ".join(n for n, _ in DEFAULT_PROGRAMS)
    scope = ep.add_mutually_exclusive_group()
    scope.add_argument("--full", action="store_true",
                       help="Evaluate all 40 programs (default: the 3 easy/medium/hard set: "
                            + default_names + ").")
    scope.add_argument("--only", nargs="+", metavar="PROGRAM",
                       help="Evaluate only these program name(s), e.g. --only sieve gcd.")
    ep.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR),
                    help="Where to export results (created if missing).")
    ep.add_argument("--label", default=None, help="Run label (default: timestamp).")
    ep.add_argument("--model", default=DEFAULT_MODEL, help=f"Model name (default: {DEFAULT_MODEL}).")
    ep.add_argument("--tokens-before", type=int, default=None, help="Session tokens before the run.")
    ep.add_argument("--tokens-after", type=int, default=None, help="Session tokens after the run.")
    ep.add_argument("--cost-usd", type=float, default=None, help="Reported cost in USD.")
    ep.add_argument("--notes", default=None, help="Free-form notes for this run.")
    ep.add_argument("--timeout", type=int, default=10, help="Per-test timeout (s). Default 10.")
    ep.add_argument("--wall-timeout", type=int, default=120,
                    help="Hard per-program wall-clock timeout (s). Default 120.")
    ep.add_argument("--runslow", action="store_true", help="Include the slow knapsack case.")
    ep.set_defaults(func=cmd_evaluate)

    cp = sub.add_parser("compare", help="Print a leaderboard of every recorded run.")
    cp.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR),
                    help="Results directory to scan.")
    cp.set_defaults(func=cmd_compare)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
