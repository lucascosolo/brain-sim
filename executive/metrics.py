"""Per-task metrics, computed from the trace and state only (nothing is counted twice by hand)."""
from __future__ import annotations

import json
from pathlib import Path


def compute(state_dir: Path | str) -> dict:
    state_dir = Path(state_dir)
    state = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
    events = [json.loads(l) for l in (state_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    actions = [e for e in events if e["kind"] == "action"]
    llm = [e for e in events if e["kind"] == "deliberation_response"]
    evals = [e for e in events if e["kind"] == "evaluation" and e.get("evaluation_of") == "edit"]
    subs = state["goals"][0]["subgoals"]
    resolved = [s for s in subs if s["status"] == "resolved"]
    resolved_without_llm = [s for s in resolved if not any(a["tier"] == "deliberation" for a in s["attempts"])]
    stated = [e for e in evals if e.get("stated_confidence") is not None]
    return {
        "task_id": state["task_id"],
        "status": state["status"],
        "completed_verified": state["status"] == "complete",
        "blocked_reason": state["blocked_reason"],
        "steps": state["step"],
        "actions_total": len(actions) + len(llm),
        "actions_deterministic": len(actions),
        "deterministic_action_fraction": round(len(actions) / (len(actions) + len(llm)), 3) if actions or llm else None,
        "llm_calls": len(llm),
        "llm_input_tokens": sum(e.get("input_tokens", 0) for e in llm),
        "llm_output_tokens": sum(e.get("output_tokens", 0) for e in llm),
        "llm_cost_usd": round(sum(e.get("cost_usd", 0.0) for e in llm), 6),
        "subgoals": len(subs),
        "subgoals_resolved": len(resolved),
        "subgoals_resolved_without_llm": len(resolved_without_llm),
        "attempts_by_outcome": _count(a["outcome"] for s in subs for a in s["attempts"]),
        "rollbacks": state["counters"]["rollbacks"],
        "recoveries": sum(1 for s in resolved if any(a["outcome"] in ("regressed", "no_effect", "edit_refused",
                                                                       "invalid_response", "llm_error") for a in s["attempts"])),
        "false_confidence": sum(1 for e in stated if e["stated_confidence"] >= 0.8 and e["outcome"] != "fixed"),
        "stated_confidence_events": len(stated),
        "human_interventions_needed": 1 if state["status"] == "blocked" else 0,
        "sandbox_denials_last_run": len(state["world"]["tests"]["sandbox_denials"]),
    }


def _count(items) -> dict:
    out: dict = {}
    for i in items:
        out[i] = out.get(i, 0) + 1
    return dict(sorted(out.items()))
