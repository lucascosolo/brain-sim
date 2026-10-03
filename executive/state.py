"""The executive's persistent state: structured data, overwritten atomically, never a transcript.

Layout of a task's state directory (outside the workspace it works on):
    state.json      current truth (this module's schema), overwritten after every step
    trace.jsonl     append-only event log (loop.py), one event per line
    reflex/         reflex-layer run dir: snapshots, quarantine, sandboxed test runs
Cross-task memory lives in a separate memory directory (memory.py).
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

SCHEMA_VERSION = 1
GOAL_STATUSES = ("active", "satisfied", "blocked")
SUBGOAL_STATUSES = ("open", "resolved", "abandoned")
TASK_STATUSES = ("active", "complete", "blocked")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def new_state(task_id: str, workspace_root: str, objective: str, priority: float,
              max_steps: int, max_deliberations_per_subgoal: int, max_deliberations_total: int) -> dict:
    t = now()
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "created_at": t,
        "updated_at": t,
        "workspace_root": workspace_root,
        "status": "active",
        "blocked_reason": None,
        "step": 0,
        "goals": [{
            "id": "g1", "kind": "tests_pass", "description": objective, "priority": priority,
            "status": "active", "subgoals": [], "unresolved_questions": [],
        }],
        "world": {
            "tests": {"known": False, "fresh": False, "observed_at_step": None, "exit_meaning": None,
                      "n_collected": 0, "passed": [], "failed": {}, "collect_errors": [],
                      "sandbox_denials": []},
            "edits": [],
        },
        "intention": None,
        "pending_prediction": None,
        "budgets": {"max_steps": max_steps,
                    "max_deliberations_per_subgoal": max_deliberations_per_subgoal,
                    "max_deliberations_total": max_deliberations_total},
        "counters": {"deliberations": 0, "actions": 0, "rollbacks": 0},
    }


def save(state: dict, path: Path) -> None:
    state["updated_at"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load(path: Path) -> dict:
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{path}: schema_version {state.get('schema_version')} is not {SCHEMA_VERSION}")
    return state


def render(state: dict) -> str:
    """Human-readable projection of the state; computed from it, never stored."""
    out = [f"TASK {state['task_id']}  status={state['status']}  step={state['step']}"
           + (f"  blocked: {state['blocked_reason']}" if state["blocked_reason"] else "")]
    out.append("ACTIVE GOALS")
    for g in state["goals"]:
        out.append(f"  {g['priority']:.2f} {g['description']}  [{g['status']}]")
    tests = state["world"]["tests"]
    if tests["known"]:
        out.append(f"WORLD  tests: {len(tests['passed'])} passed, {len(tests['failed'])} failed, "
                   f"{len(tests['collect_errors'])} collection errors"
                   + ("" if tests["fresh"] else "  (stale: workspace changed since last run)"))
    else:
        out.append("WORLD  tests: unknown")
    kept = [e for e in state["world"]["edits"] if e["kept"]]
    if kept:
        out.append(f"       edits kept: {len(kept)} ({', '.join(e['operator'] for e in kept)})")
    questions = [q for g in state["goals"] for q in g["unresolved_questions"]]
    subs = [s for g in state["goals"] for s in g["subgoals"]]
    open_q = [s["question"] for s in subs if s["status"] == "open"] + questions
    if open_q:
        out.append("UNRESOLVED QUESTIONS")
        out += [f"  - {q}" for q in open_q]
    out.append(f"CURRENT INTENTION\n  {state['intention'] or 'none'}")
    if subs:
        out.append("SUBGOALS")
        mark = {"resolved": "✓", "abandoned": "✗", "open": "○"}
        for s in sorted(subs, key=lambda s: -s["salience"]):
            tried = ", ".join(f"{a['operator']}→{a['outcome']}" for a in s["attempts"]) or "no attempts"
            out.append(f"  {mark[s['status']]} {s['salience']:.2f} {s['target']}  ({tried})")
    return "\n".join(out)
