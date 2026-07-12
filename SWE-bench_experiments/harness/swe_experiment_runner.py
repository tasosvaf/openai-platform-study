#!/usr/bin/env python3
"""Experiment harness for the SWE-bench Lite assignment (the "second 3").

Companion to the QuixBugs harness. Where the QuixBugs runner *runs* pytest, this
one *collects* the results that the SWE-bench Docker harness
(``run_experiment.sh`` / ``run_all.sh``) already produced, and exports them in the
same comparable shape — one folder per tool, per-run diffs, token cost and a
qualitative scorecard — into the ``SWE-bench_results`` folder.

Workflow
--------
1. Put the agent's patch for each level into ``predictions/<level>.jsonl`` (set
   ``model_patch`` and ``model_name_or_path``). See ../README.md > "Use your own
   model".

2. Run the SWE-bench evaluation (builds/apply/test in Docker)::

       ./run_experiment.sh all 2 --local     # or ./run_all.sh on Apple Silicon

   This writes ``<model>.assignment-<level>.json`` and
   ``logs/run_evaluation/assignment-<level>/<model>/<instance_id>/``.

3. Collect + export the run::

       python3 harness/swe_experiment_runner.py evaluate \
           --tool aider --model gpt-5.1 \
           --tokens-before 0 --tokens-after 240000 --cost-usd 1.20

4. Compare every recorded run::

       python3 harness/swe_experiment_runner.py compare
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
ASSIGN_DIR = HARNESS_DIR.parent  # the SWE-bench_experiments/ folder

# Base results folder shared by both benchmarks; each benchmark writes into its
# own subfolder beneath it.
EXPERIMENT_RESULTS_ROOT = Path("/Users/tasosvaf/repos/testRepos/experiment_results")
DEFAULT_RESULTS_DIR = EXPERIMENT_RESULTS_ROOT / "SWE-bench_results"

# Default model recorded on a run unless overridden with --model.
DEFAULT_MODEL = "GPT 5.4-mini"

# slug -> human readable display name. The slug is the folder name on disk.
# Kept identical to the QuixBugs harness so results line up tool-for-tool.
TOOLS = {
    "github_copilot_cli": "GitHub Copilot CLI",
    "vscode_copilot_cli": "VS Code Copilot CLI",
    "cline": "Cline",
    "aider": "Aider",
    "openai_codex_cli": "OpenAI Codex CLI",
    "openai_codex_ui": "OpenAI Codex UI",
}

# The three SWE-bench Lite experiments, easy -> medium -> hard. The instance id is
# read from predictions/<level>.jsonl at runtime; the repo label here is only for
# display.
LEVELS = ["easy", "medium", "hard"]
REPO_BY_LEVEL = {
    "easy": "matplotlib",
    "medium": "sympy",
    "hard": "django",
}

# Same qualitative rubric as the QuixBugs harness.
RUBRIC = [
    ("Diagnosis quality", "Did it find the true / likely root cause?"),
    ("Evidence use", "Did it cite specific files, lines, logs, or docs?"),
    ("Hallucination risk", "Did it invent APIs, files, or assumptions?"),
    ("Missing-context behavior", "Did it ask useful clarifying questions?"),
    ("Fix quality", "Was the proposed fix safe and minimal?"),
    ("Test quality", "Did it propose a meaningful regression test?"),
    ("Platform insight", "What does this reveal about the agent platform?"),
]

STATUS_LABEL = {
    "pass": "RESOLVED",
    "fail": "UNRESOLVED",
    "empty": "EMPTY",
    "error": "ERROR",
    "missing": "NOT RUN",
}


def _timestamp():
    return _dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def _load_predictions(level):
    """Return the list of prediction dicts in predictions/<level>.jsonl."""
    path = ASSIGN_DIR / "predictions" / f"{level}.jsonl"
    preds = []
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    preds.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return preds


def _load_report(model_np, level):
    """Load the SWE-bench summary report for a model + level, if present."""
    path = ASSIGN_DIR / f"{model_np}.assignment-{level}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return None
    return None


def _status_for(instance_id, report):
    if report is None:
        return "missing"
    if instance_id in report.get("resolved_ids", []):
        return "pass"
    if instance_id in report.get("empty_patch_ids", []):
        return "empty"
    if instance_id in report.get("error_ids", []):
        return "error"
    if instance_id in report.get("unresolved_ids", []):
        return "fail"
    return "missing"


def _instance_log_dir(model_np, level, instance_id):
    return (
        ASSIGN_DIR / "logs" / "run_evaluation" / f"assignment-{level}"
        / model_np / instance_id
    )


def _tests_status(model_np, level, instance_id):
    """Return (f2p_passed, f2p_total, p2p_passed, p2p_total) from report.json."""
    p = _instance_log_dir(model_np, level, instance_id) / "report.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError:
        return None
    ts = data.get(instance_id, {}).get("tests_status", {})
    f2p = ts.get("FAIL_TO_PASS", {})
    p2p = ts.get("PASS_TO_PASS", {})
    f2p_ok = len(f2p.get("success", []))
    f2p_total = f2p_ok + len(f2p.get("failure", []))
    p2p_ok = len(p2p.get("success", []))
    p2p_total = p2p_ok + len(p2p.get("failure", []))
    return f2p_ok, f2p_total, p2p_ok, p2p_total


# --------------------------------------------------------------------------- #
# evaluate
# --------------------------------------------------------------------------- #
def cmd_evaluate(args):
    tool_slug = args.tool
    tool_name = TOOLS[tool_slug]

    results_dir = Path(args.results_dir).expanduser()
    label = args.label or _timestamp()
    run_dir = results_dir / tool_slug / f"run_{label}"
    diffs_dir = run_dir / "diffs"
    diffs_dir.mkdir(parents=True, exist_ok=True)

    if args.only:
        unknown = [lv for lv in args.only if lv not in LEVELS]
        if unknown:
            print(f"[evaluate] unknown level(s): {', '.join(unknown)}. "
                  f"Valid: {', '.join(LEVELS)}.", file=sys.stderr)
            return 1
        targets = list(args.only)
    else:
        targets = list(LEVELS)

    print(f"[evaluate] {tool_name}: collecting {len(targets)} SWE-bench level(s)...")

    per_instance = {}
    full_output_chunks = []
    counts = {k: 0 for k in STATUS_LABEL}
    swe_model_names = set()

    for level in targets:
        preds = _load_predictions(level)
        if not preds:
            print(f"  [{level}] no predictions/{level}.jsonl entry — skipping.",
                  file=sys.stderr)
            continue
        for pred in preds:
            instance_id = pred.get("instance_id", f"<unknown-{level}>")
            model_np = pred.get("model_name_or_path", "")
            swe_model_names.add(model_np)
            report = _load_report(model_np, level)
            status = _status_for(instance_id, report)
            counts[status] = counts.get(status, 0) + 1

            # diff: the patch the agent proposed for this instance.
            patch = pred.get("model_patch") or ""
            log_dir = _instance_log_dir(model_np, level, instance_id)
            applied = log_dir / "patch.diff"
            if applied.exists():
                patch = applied.read_text()
            diff_path = None
            if patch.strip():
                diff_path = diffs_dir / f"{instance_id}.diff"
                diff_path.write_text(patch)

            tests = _tests_status(model_np, level, instance_id)
            test_log = log_dir / "test_output.txt"
            test_log_rel = None
            if test_log.exists():
                test_log_rel = str(test_log)

            per_instance[instance_id] = {
                "level": level,
                "repo": REPO_BY_LEVEL.get(level),
                "swe_model_name": model_np,
                "status": status,
                "resolved": status == "pass",
                "fail_to_pass": (f"{tests[0]}/{tests[1]}" if tests else None),
                "pass_to_pass": (f"{tests[2]}/{tests[3]}" if tests else None),
                "diff": (str(diff_path.relative_to(run_dir)) if diff_path else None),
                "test_log": test_log_rel,
            }
            f2p = per_instance[instance_id]["fail_to_pass"]
            print(f"  {level:<7} {instance_id:<32} {STATUS_LABEL[status]:>11}"
                  + (f"  FAIL_TO_PASS {f2p}" if f2p else ""))

            body = ""
            if test_log.exists():
                body = test_log.read_text()
            full_output_chunks.append(
                "=" * 70
                + f"\n### {level} — {instance_id} -> {STATUS_LABEL[status]}"
                + "\n" + "=" * 70 + "\n" + body.rstrip() + "\n"
            )

    total = len(per_instance)
    fixed = counts["pass"]

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

    summary = {
        "benchmark": "SWE-bench Lite",
        "tool_slug": tool_slug,
        "tool_name": tool_name,
        "model": args.model,
        "swe_model_name": sorted(n for n in swe_model_names if n),
        "label": label,
        "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
        "total_instances": total,
        "resolved": fixed,
        "resolve_rate": round(fixed / total, 4) if total else 0.0,
        "counts": counts,
        "tokens": tokens,
        "notes": args.notes,
        "per_instance": per_instance,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (run_dir / "test_output.txt").write_text("\n".join(full_output_chunks))

    _write_summary_md(run_dir, summary)
    _write_scorecard_md(run_dir, summary)
    _write_tool_index(results_dir, tool_slug)
    _write_top_readme(results_dir)

    print("\n" + "-" * 70)
    print(f"[evaluate] {tool_name}: {fixed}/{total} resolved "
          f"({summary['resolve_rate'] * 100:.1f}%).")
    if tokens_delta is not None:
        print(f"[evaluate] tokens used: {tokens_delta:,}"
              + (f"  (~${args.cost_usd})" if args.cost_usd is not None else ""))
    if counts["missing"]:
        print(f"[evaluate] note: {counts['missing']} level(s) had no SWE-bench "
              f"report yet — run ./run_experiment.sh first.")
    print(f"[evaluate] results -> {run_dir}")
    print(f"[evaluate] fill in the qualitative rubric: {run_dir / 'scorecard.md'}")
    return 0


def _write_summary_md(run_dir: Path, s: dict):
    lines = [
        f"# {s['tool_name']} — SWE-bench run `{s['label']}`",
        "",
        f"- **Benchmark:** {s['benchmark']}",
        f"- **Timestamp:** {s['timestamp']}",
        f"- **Model:** {s['model'] or '_(unspecified)_'}",
        f"- **Resolved:** {s['resolved']} / {s['total_instances']} "
        f"({s['resolve_rate'] * 100:.1f}%)",
        f"- **Resolved / Unresolved / Empty / Error / Not-run:** "
        f"{s['counts']['pass']} / {s['counts']['fail']} / {s['counts']['empty']} / "
        f"{s['counts']['error']} / {s['counts']['missing']}",
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
        "## Per-instance results",
        "",
        "| Level | Instance | Repo | Result | FAIL_TO_PASS | Diff |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for inst, p in s["per_instance"].items():
        diff = f"[patch]({p['diff']})" if p["diff"] else "—"
        f2p = p["fail_to_pass"] or "—"
        lines.append(
            f"| {p['level']} | {inst} | {p['repo'] or '—'} | "
            f"{STATUS_LABEL[p['status']]} | {f2p} | {diff} |"
        )
    lines.append("")
    (run_dir / "summary.md").write_text("\n".join(lines))


def _write_scorecard_md(run_dir: Path, s: dict):
    scorecard = run_dir / "scorecard.md"
    if scorecard.exists():
        return
    lines = [
        f"# Qualitative scorecard — {s['tool_name']} (SWE-bench run `{s['label']}`)",
        "",
        "Fill this in after inspecting the run. Score each criterion 1–5 and add",
        "evidence (file/line references, quotes from the agent transcript, links to",
        "the SWE-bench `test_output.txt`).",
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
        f"- Resolved: **{s['resolved']} / {s['total_instances']}** "
        f"({s['resolve_rate'] * 100:.1f}%)",
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
    rows = ["| Run | Resolved | Rate | Tokens | Cost |",
            "| --- | ---: | ---: | ---: | ---: |"]
    for run_dir, s in _iter_runs(tool_dir):
        t = s.get("tokens", {})
        tok = f"{t['tokens_used']:,}" if t.get("tokens_used") is not None else "—"
        cost = f"${t['cost_usd']}" if t.get("cost_usd") is not None else "—"
        rows.append(
            f"| [{run_dir.name}]({run_dir.name}/summary.md) | "
            f"{s['resolved']}/{s['total_instances']} | "
            f"{s['resolve_rate'] * 100:.1f}% | {tok} | {cost} |"
        )
    content = [f"# {TOOLS.get(tool_slug, tool_slug)} — SWE-bench runs", ""] + rows + [""]
    tool_dir.mkdir(parents=True, exist_ok=True)
    (tool_dir / "index.md").write_text("\n".join(content))


def _write_top_readme(results_dir: Path):
    lines = [
        "# SWE-bench Lite — agent comparison results",
        "",
        "Auto-generated. Each subfolder is one agent/platform; each `run_*` is one",
        "evaluated experiment (easy/medium/hard). See",
        "`SWE-bench_experiments/harness/README.md` for how to reproduce a run.",
        "",
        "## Latest run per tool",
        "",
        "| Tool | Latest run | Resolved | Rate | Tokens | Cost |",
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
            f"{s['resolved']}/{s['total_instances']} | "
            f"{s['resolve_rate'] * 100:.1f}% | {tok} | {cost} |"
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
    header = f"{'Tool':<24}{'Run':<20}{'Resolved':>10}{'Rate':>8}{'Tokens':>12}{'Cost':>10}"
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
                f"{s['resolved']}/{s['total_instances']:<8}"
                f"{s['resolve_rate'] * 100:>6.1f}%{tok:>12}{cost:>10}"
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

    ep = sub.add_parser("evaluate", help="Collect SWE-bench results and export a result set.")
    ep.add_argument("--tool", required=True, choices=sorted(TOOLS), help="Agent/platform.")
    ep.add_argument("--only", nargs="+", metavar="LEVEL", choices=LEVELS,
                    help="Collect only these level(s): easy medium hard.")
    ep.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR),
                    help="Where to export results (created if missing).")
    ep.add_argument("--label", default=None, help="Run label (default: timestamp).")
    ep.add_argument("--model", default=DEFAULT_MODEL, help=f"Model name for the report (default: {DEFAULT_MODEL}).")
    ep.add_argument("--tokens-before", type=int, default=None, help="Session tokens before the run.")
    ep.add_argument("--tokens-after", type=int, default=None, help="Session tokens after the run.")
    ep.add_argument("--cost-usd", type=float, default=None, help="Reported cost in USD.")
    ep.add_argument("--notes", default=None, help="Free-form notes for this run.")
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
