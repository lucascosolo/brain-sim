"""Command line: python -m executive {run,status,metrics,bench} ...

Derived data defaults to ~/.cache/brain-sim/executive/ (never /tmp: tmpfs on the owner's PC).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

from . import demo_tasks, metrics
from .deliberation import ClaudeCLIDeliberator, RecordingDeliberator, ReplayDeliberator
from .loop import Executive
from .state import load, render

CACHE = Path.home() / ".cache" / "brain-sim" / "executive"
RESULTS = Path(__file__).resolve().parent.parent / "bench" / "results"


def _stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def cmd_run(a) -> int:
    state_dir = Path(a.state_dir or CACHE / "tasks" / _stamp())
    deliberator = None
    if a.deliberator == "claude-cli":
        deliberator = RecordingDeliberator(ClaudeCLIDeliberator(state_dir / "deliberation-cwd", model=a.model,
                                                                max_budget_usd=a.max_budget_usd),
                                           state_dir / "cassette.jsonl")
    elif a.deliberator == "replay":
        deliberator = ReplayDeliberator(a.cassette)
    ex = Executive(a.repo, state_dir, a.memory_dir or CACHE / "memory", deliberator=deliberator,
                   objective=a.objective, max_steps=a.max_steps)
    ex.run()
    print(render(ex.state))
    print(json.dumps(metrics.compute(state_dir), indent=1))
    print(f"state: {state_dir}")
    return 0 if ex.state["status"] == "complete" else 2


def cmd_status(a) -> int:
    print(render(load(Path(a.state_dir) / "state.json")))
    return 0


def cmd_metrics(a) -> int:
    print(json.dumps(metrics.compute(a.state_dir), indent=1))
    return 0


# (task, builder, scripted deliberator, memory). Each task gets a fresh memory except the repeat,
# which reuses logic_bug's memory to show a model-dependent fix becoming a model-free one.
BENCH = [
    ("passing", demo_tasks.task_passing, None, "own"),
    ("typo", demo_tasks.task_typo, demo_tasks.good_model, "own"),
    ("missing_import", demo_tasks.task_missing_import, demo_tasks.good_model, "own"),
    ("logic_bug", demo_tasks.task_logic_bug, demo_tasks.good_model, "own"),
    ("logic_bug_repeat_with_memory", demo_tasks.task_logic_bug, demo_tasks.good_model, "logic_bug"),
    ("logic_bug_bad_first_answer", demo_tasks.task_logic_bug, demo_tasks.wrong_then_right_model, "own"),
    ("logic_bug_model_edits_tests", demo_tasks.task_logic_bug, demo_tasks.test_editing_model, "own"),
    ("logic_bug_malformed_answer", demo_tasks.task_logic_bug, demo_tasks.malformed_model, "own"),
    ("logic_bug_no_model", demo_tasks.task_logic_bug, None, "own"),
]


def cmd_bench(a) -> int:
    work = Path(a.work_dir or CACHE / "bench" / _stamp())
    commit = subprocess.run(["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    rows = []
    for name, build, model, mem in BENCH:
        memory = work / (name if mem == "own" else mem) / "memory"
        repo = work / name / "repo"
        repo.mkdir(parents=True)
        build(repo)
        ex = Executive(repo, work / name / "state", memory, deliberator=model() if model else None, task_id=name)
        ex.run()
        m = metrics.compute(work / name / "state")
        rows.append({"recorded_at": _stamp(), "experiment": "executive-demo", "commit": commit,
                     "deliberator": model().name if model else None, "memory": mem, "task": name, **m})
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = Path(a.out or RESULTS / "executive_demo.jsonl")
    with out.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    cols = ["task", "status", "steps", "actions_total", "llm_calls", "rollbacks", "subgoals_resolved_without_llm",
            "false_confidence"]
    print("  ".join(f"{c:>{max(len(c), 28 if c == 'task' else 0)}}" for c in cols))
    for r in rows:
        print("  ".join(f"{str(r[c]):>{max(len(c), 28 if c == 'task' else 0)}}" for c in cols))
    print(f"appended {len(rows)} rows to {out}; work dir {work}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m executive")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="work on a repository until its tests pass, or block")
    r.add_argument("--repo", required=True, type=Path)
    r.add_argument("--state-dir", type=Path)
    r.add_argument("--memory-dir", type=Path)
    r.add_argument("--objective", default="Make the test suite pass")
    r.add_argument("--deliberator", choices=["none", "claude-cli", "replay"], default="none")
    r.add_argument("--model", default="haiku")
    r.add_argument("--max-budget-usd", type=float, default=0.25, help="per deliberation call (claude-cli)")
    r.add_argument("--cassette", type=Path, help="recorded responses (replay)")
    r.add_argument("--max-steps", type=int, default=40)
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("status", help="render a task's state")
    s.add_argument("--state-dir", required=True, type=Path)
    s.set_defaults(fn=cmd_status)
    m = sub.add_parser("metrics", help="metrics of a task from its trace")
    m.add_argument("--state-dir", required=True, type=Path)
    m.set_defaults(fn=cmd_metrics)
    b = sub.add_parser("bench", help="run the demo tasks with scripted deliberators (loop mechanics only)")
    b.add_argument("--work-dir", type=Path)
    b.add_argument("--out", type=Path)
    b.set_defaults(fn=cmd_bench)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
