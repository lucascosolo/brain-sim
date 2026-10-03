"""The executive loop. Plain code: sense, decide, act, predict, observe, evaluate, repeat.

One step = one decision. Decisions, in order of precedence:
  1. observe   the test facts are unknown or stale (the workspace changed since the last run)
               -> run the sandboxed suite; then evaluate any pending prediction against it
  2. complete  the facts are fresh and every collected test passes
  3. attempt   pick the most salient open subgoal; pick the cheapest applicable operator
               that has not already failed with the same plan; apply its edits; predict
  4. abandon   impasse on a subgoal and no deliberation is available or affordable
  5. block     no open subgoal can make progress, or the step budget is spent

Only operator tier 5 (deliberation) calls a language model, and only from step 3.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import uuid
from pathlib import Path

from reflex import EXECUTE_SANDBOXED, READ_ONLY, WRITE_WORKSPACE, Workspace, default_registry

from . import gaming
from . import state as st
from .deliberation import PATCH_SCHEMA, DeliberationRequest, validate_patch
from .memory import Memory
from .operators import (TIER_NAMES, TIER_REFLEX, AddMissingImport, DeliberatePatch, FixNameTypo, Plan,
                        RecallVerifiedFix)
from .signatures import context_hash, signature

DEFAULT_PROTECTED = ("tests/*", "test_*.py", "*/test_*.py", "*_test.py", "conftest.py", "*/conftest.py",
                     # test configuration decides what runs; editing it can "fix" by deselection (F4)
                     "pytest.ini", "*/pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini")
PROJECTION_FILE_LINES = 150
# Scope guard: a model-proposed change larger than this is outside what the executive can verify
# cheaply. It is not applied; the subgoal is handed off (abandoned with a reason) instead.
MAX_DELIBERATION_FILES = 2
MAX_PROJECTION_FILES = 6
MAX_DELIBERATION_CHANGED_LINES = 30
PATH_LINE_RE = re.compile(r"^(?P<path>[\w./-]+\.py):(?P<line>\d+)")


def _fp(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


class Executive:
    def __init__(self, workspace_root: Path | str, state_dir: Path | str, memory_dir: Path | str,
                 deliberator=None, objective: str = "Make the test suite pass", priority: float = 0.9,
                 max_steps: int = 40, max_deliberations_per_subgoal: int = 2, max_deliberations_total: int = 4,
                 protected: tuple[str, ...] = DEFAULT_PROTECTED, task_id: str | None = None, registry=None,
                 env_guard: bool = True):
        self.state_dir = Path(state_dir)
        self.state_path = self.state_dir / "state.json"
        self.trace_path = self.state_dir / "trace.jsonl"
        self.ws = Workspace(workspace_root, self.state_dir / "reflex", protected=protected)
        self.registry = registry or default_registry()
        self.memory = Memory(memory_dir)
        self.deliberator = deliberator
        self.env_guard = env_guard           # False only for the E6 ablation that shows what the guard prevents
        self.operators = [RecallVerifiedFix(), FixNameTypo(), AddMissingImport(), DeliberatePatch()]
        if self.state_path.exists():
            self.state = st.load(self.state_path)
            if self.state["workspace_root"] != str(self.ws.root):
                raise ValueError("state directory belongs to a different workspace")
            self._seq = sum(1 for _ in self.trace_path.open(encoding="utf-8")) if self.trace_path.exists() else 0
            self.trace("task_resumed", step_budget=max_steps)
            self.state["budgets"]["max_steps"] = max_steps
        else:
            self._seq = 0
            self.state = st.new_state(task_id or uuid.uuid4().hex[:12], str(self.ws.root), objective, priority,
                                      max_steps, max_deliberations_per_subgoal, max_deliberations_total)
            self.trace("task_created", objective=objective, workspace_root=str(self.ws.root),
                       deliberator=getattr(deliberator, "name", None), protected=list(protected))
            st.save(self.state, self.state_path)

    # ---- plumbing ----------------------------------------------------------------------
    def trace(self, kind: str, **payload) -> None:
        self._seq += 1
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with self.trace_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"seq": self._seq, "at": st.now(), "step": self.state["step"], "kind": kind,
                                **payload}, sort_keys=True) + "\n")

    def reflex(self, capability: str, effect: str, **params):
        """Invoke one capability, granting only the single effect the caller says it needs."""
        r = self.registry.invoke(capability, self.ws, [effect], **params)
        self.state["counters"]["actions"] += 1
        self.trace("action", tier=TIER_NAMES[TIER_REFLEX], capability=capability, ok=r.ok, error=r.error,
                   duration_ms=round(r.duration_ms, 1), uses_llm=False)
        return r

    @property
    def goal(self) -> dict:
        return self.state["goals"][0]

    def _subgoal(self, sid: str) -> dict:
        return next(s for s in self.goal["subgoals"] if s["id"] == sid)

    # ---- loop --------------------------------------------------------------------------
    def run(self) -> dict:
        while self.state["status"] == "active":
            if self.state["step"] >= self.state["budgets"]["max_steps"]:
                self._block(f"step budget of {self.state['budgets']['max_steps']} spent")
                break
            self.step()
        st.save(self.state, self.state_path)
        return self.state

    def step(self) -> None:
        self.state["step"] += 1
        tests = self.state["world"]["tests"]
        if not tests["fresh"]:
            self.trace("decision", decision="observe", reason="test facts unknown" if not tests["known"]
                       else "workspace changed since the last observation")
            self._observe()
        elif self._baseline_lost():
            self._block(self._baseline_lost())
        elif self._satisfied():
            self.trace("decision", decision="complete", reason="fresh run: every collected test passes")
            self.goal["status"] = "satisfied"
            self.state["status"] = "complete"
            self.state["intention"] = None
            self.trace("goal_satisfied", goal=self.goal["id"], n_passed=len(tests["passed"]))
        elif tests["n_collected"] == 0 and not tests["collect_errors"]:
            self._block("no tests were collected, so nothing can verify the goal")
        else:
            self._work_on_subgoal()
        st.save(self.state, self.state_path)

    def _satisfied(self) -> bool:
        t = self.state["world"]["tests"]
        return (t["fresh"] and t["exit_meaning"] == "all_passed" and t["n_collected"] > 0
                and not t["failed"] and not t["collect_errors"] and not self._baseline_lost())

    def _baseline_lost(self) -> str | None:
        """Tests that ran at the start must still be collected, and none may have become a skip.

        Without this, an edit can make a suite "pass" by making tests vanish or skip
        (review finding F4: a deselecting config; a library-side pytest.skip).
        """
        t = self.state["world"]["tests"]
        base = t.get("baseline")
        if not (t["fresh"] and base and t.get("exit_meaning") in ("all_passed", "tests_failed")):
            return None
        missing = sorted(set(base["collected"]) - set(t.get("collected") or []))
        now_skipped = sorted(set(base["ran"]) & set(t.get("skipped") or []))
        if missing:
            return f"tests collected at the start are no longer collected: {missing[:5]}"
        if now_skipped:
            return f"tests that ran at the start are now skipped: {now_skipped[:5]}"
        return None

    def _restore_unverified_edits(self) -> None:
        """On block, hand back the original tree unless every kept edit is a verified fix (F5).

        All kept edits are restored, newest first, when any one of them is unverified: a later
        edit may sit on top of an earlier one in the same file, so restoring only some of them
        could leave a mixture that never existed.
        """
        kept = [e for e in self.state["world"]["edits"] if e["kept"]]
        if not kept or all(e.get("outcome") == "fixed" for e in kept):
            return
        for e in reversed(kept):
            for rec in reversed(e["write_records"]):
                self.reflex("fs.restore", WRITE_WORKSPACE, write_record=rec)
            e["kept"] = False
            e["restored_on_block"] = True
        pending = self.state["pending_prediction"]
        if pending and pending.get("kind") == "edit":
            # the restored edit was never evaluated: close its attempt so a resumed run re-observes
            sub = self._subgoal(pending["subgoal"])
            for a in sub["attempts"]:
                if a["outcome"] == "pending":
                    a["outcome"] = "restored_on_block"
        self.state["pending_prediction"] = None
        self.state["world"]["tests"]["fresh"] = False
        self.trace("restored_on_block", edits=[e["edit_id"] for e in kept],
                   unverified=[e["edit_id"] for e in kept if e.get("outcome") != "fixed"])

    def _block(self, reason: str) -> None:
        self._restore_unverified_edits()
        self.state["status"] = "blocked"
        self.state["blocked_reason"] = reason
        conflict = any((s.get("resolution") or "").startswith("conflict") for s in self.goal["subgoals"])
        self.state["escalate_to"] = "human" if conflict else "agent"
        self.goal["status"] = "blocked"
        self.state["intention"] = None
        self.trace("goal_blocked", goal=self.goal["id"], reason=reason)

    # ---- sensing -----------------------------------------------------------------------
    def _observe(self) -> None:
        r = self.reflex("tests.run_pytest", EXECUTE_SANDBOXED)
        if not r.ok:
            self._block(f"could not run the test suite: {r.error}")
            return
        d = r.data
        tests = self.state["world"]["tests"]
        tests.update(known=True, fresh=True, observed_at_step=self.state["step"], exit_meaning=d["exit_meaning"],
                     n_collected=d["n_collected"], passed=d["passed"], failed=d["failed"],
                     collect_errors=d["collect_errors"], sandbox_denials=d["sandbox_denials"],
                     collected=d.get("collected", []), skipped=d.get("skipped", []))
        if tests.get("baseline") is None and d["exit_meaning"] in ("all_passed", "tests_failed"):
            tests["baseline"] = {"collected": sorted(d.get("collected", [])),
                                 "ran": sorted(set(d["passed"]) | set(d["failed"]))}
        self.trace("observation", exit_meaning=d["exit_meaning"], n_passed=len(d["passed"]),
                   failed=sorted(d["failed"]), collect_errors=[c["nodeid"] for c in d["collect_errors"]],
                   sandbox_denials=len(d["sandbox_denials"]), duration_ms=d["duration_ms"])
        if d["exit_meaning"] == "sandbox_refused" and self.env_guard:
            # Some tests cannot run in the sandbox, so their outcome is unknown and the goal
            # cannot be verified here. Hand the task off before editing anything.
            refused = sorted(d.get("refused") or {})
            self.trace("handoff", subgoal=None, target=refused[:5], reason="sandbox_denied",
                       events=sorted({x["event"] for x in d["sandbox_denials"]}))
            self._block(f"the sandbox refused what {len(refused)} test(s) need ({refused[:3]}); "
                        "their outcomes are unknown, so the goal cannot be verified here")
            return
        if d["exit_meaning"] not in ("all_passed", "tests_failed", "no_tests_collected"):
            # an allowlist, so a new runner outcome (report_unverified, unknown) blocks by default
            problems = "; ".join(d.get("integrity_problems") or [])
            self._block(f"test runner ended with {d['exit_meaning']}" + (f": {problems}" if problems else ""))
            return
        pending = self.state["pending_prediction"]
        if pending is not None:
            self.state["pending_prediction"] = None
            if pending["kind"] == "edit":
                self._evaluate_edit(pending)
            else:
                self._evaluate_rollback(pending)
        # A rollback just made this observation stale; subgoals sync on the next (fresh) one.
        if self.state["status"] == "active" and tests["fresh"]:
            self._sync_subgoals()

    def _failures(self) -> dict:
        t = self.state["world"]["tests"]
        out = dict(t["failed"])
        for c in t["collect_errors"]:
            frames = []
            for line in (c.get("longrepr") or "").splitlines():
                m = PATH_LINE_RE.match(line.strip())
                if m:
                    try:
                        self.ws.resolve(m["path"])
                        frames.append({"path": m["path"], "line": int(m["line"]), "func": "<module>"})
                    except Exception:
                        pass
            out[c["nodeid"]] = {"nodeid": c["nodeid"], "when": "collect", "exc_type": c["exc_type"],
                                "exc_message": c["exc_message"], "frames": frames, "longrepr": c["longrepr"]}
        return out

    def _sync_subgoals(self) -> None:
        failures = self._failures()
        by_target = {s["target"]: s for s in self.goal["subgoals"]}
        for s in self.goal["subgoals"]:
            if s["status"] == "open" and s["target"] not in failures:
                s["status"] = "resolved"
                s["resolution"] = s.get("resolution") or "no longer failing (collateral of another edit)"
                self.trace("subgoal_resolved", subgoal=s["id"], target=s["target"], resolution=s["resolution"])
        for target in sorted(failures):
            f = failures[target]
            sig, ctx = signature(f), context_hash(self.ws, f)
            s = by_target.get(target)
            if s is None:
                s = {"id": f"{self.goal['id']}.s{len(self.goal['subgoals']) + 1}", "kind": "test_passes",
                     "target": target, "status": "open", "question": f"Why does {target} fail?",
                     "salience": self.goal["priority"], "attempts": [], "rejected_plans": [],
                     "signature": sig, "context_hash": ctx, "resolution": None}
                self.goal["subgoals"].append(s)
                self.trace("subgoal_created", subgoal=s["id"], target=target, signature=sig)
            else:
                if s["status"] == "resolved":
                    s["status"] = "open"
                    s["resolution"] = None
                    self.trace("subgoal_reopened", subgoal=s["id"], target=target)
                s["signature"], s["context_hash"] = sig, ctx

    # ---- deciding and acting -----------------------------------------------------------
    def _work_on_subgoal(self) -> None:
        failures = self._failures()
        open_subs = sorted((s for s in self.goal["subgoals"] if s["status"] == "open"),
                           key=lambda s: (-s["salience"], s["target"]))
        if not open_subs:
            self._block("failures remain but every subgoal is abandoned: " +
                        "; ".join(f"{s['target']}: {s['resolution']}" for s in self.goal["subgoals"] if s["status"] == "abandoned"))
            return
        sub = open_subs[0]
        failure = failures[sub["target"]]
        if self.env_guard and "reflex sandbox:" in (failure.get("exc_message") or "") + (failure.get("longrepr") or "")[-2000:]:
            # The test failed because the sandbox refused something (a subprocess, a write outside
            # the run dir). That is the environment, not a code bug: editing code to dodge the
            # sandbox would damage correct code. Hand off without touching anything.
            sub["status"] = "abandoned"
            sub["resolution"] = "handed off: environment, the sandbox refused an operation this test needs"
            self.trace("decision", decision="abandon", subgoal=sub["id"], candidates=[],
                       reason="sandbox denial is an environment limit, not a code bug")
            self.trace("handoff", subgoal=sub["id"], target=sub["target"], reason="sandbox_denied")
            return
        regressed = [set(a.get("regressions") or []) for a in sub["attempts"] if a["outcome"] == "regressed"]
        if len(regressed) >= 2 and set.intersection(*regressed):
            # Every attempted fix for this test broke the same other test(s): strong evidence that
            # the two requirements contradict each other. That needs a human decision, not
            # another model, and not the agent tier (E6: Haiku handoff agents broke tests here).
            clash = sorted(set.intersection(*regressed))
            sub["status"] = "abandoned"
            sub["resolution"] = (f"conflict: every fix for {sub['target']} broke {', '.join(clash)}; "
                                 "the requirements look contradictory and need a human decision")
            self.goal["unresolved_questions"].append(f"Which should win: {sub['target']} or {', '.join(clash)}?")
            self.trace("decision", decision="abandon", subgoal=sub["id"], candidates=[], reason="requirements conflict")
            self.trace("handoff", subgoal=sub["id"], target=sub["target"], reason="conflict_needs_human", clash=clash)
            return
        candidates = []
        for op in self.operators:
            a = op.applicable(self, sub, failure)
            plan_fp = _fp(a.plan.edits) if a.plan else None
            if a.ok and plan_fp and [op.name, plan_fp] in sub["rejected_plans"]:
                a.ok, a.reason = False, "this exact plan already failed on this subgoal"
            prior = self.memory.operator_prior(op.name, sub["signature"]["class"])
            candidates.append({"operator": op, "ok": a.ok, "reason": a.reason, "plan": a.plan, "prior": prior})
        viable = [c for c in candidates if c["ok"]]
        viable.sort(key=lambda c: (c["operator"].tier, -c["prior"]["p_fixed"], c["operator"].name))
        listing = [{"operator": c["operator"].name, "tier": TIER_NAMES[c["operator"].tier], "ok": c["ok"],
                    "reason": c["reason"], "p_fixed": round(c["prior"]["p_fixed"], 3), "n": c["prior"]["n"]}
                   for c in candidates]
        if not viable:
            sub["status"] = "abandoned"
            sub["resolution"] = "impasse: " + "; ".join(f"{c['operator'].name}: {c['reason']}" for c in candidates)
            self.trace("decision", decision="abandon", subgoal=sub["id"], candidates=listing)
            self.trace("impasse", subgoal=sub["id"], target=sub["target"], deliberation_available=False)
            return
        choice = viable[0]
        op = choice["operator"]
        if op.uses_llm:
            self.trace("impasse", subgoal=sub["id"], target=sub["target"], deliberation_available=True)
        self.state["intention"] = f"{op.name} on {sub['target']}"
        self.trace("decision", decision="attempt", subgoal=sub["id"], operator=op.name, tier=TIER_NAMES[op.tier],
                   reason=choice["reason"], candidates=listing)
        plan = choice["plan"] if not op.uses_llm else self._deliberate(sub, failure)
        if isinstance(plan, str):            # deliberation failed; plan holds the outcome name
            self._record_attempt(sub, op, None, plan, prediction_error=None, note="no edits applied")
            if plan in ("no_evidence", "model_abstained"):
                # Retrying cannot help: hand off now instead of spending more.
                sub["status"] = "abandoned"
                sub["resolution"] = f"handed off: {plan.replace('_', ' ')}"
                self.trace("handoff", subgoal=sub["id"], target=sub["target"], reason=plan)
            return
        too_big = (self._out_of_scope(plan) if op.uses_llm else None) or \
            gaming.suspicious(self.ws.root, plan.edits, sub["target"])
        if too_big:
            self._record_attempt(sub, op, plan, "out_of_scope", prediction_error=None, note=too_big)
            sub["status"] = "abandoned"
            sub["resolution"] = f"handed off: {too_big}"
            self.trace("handoff", subgoal=sub["id"], target=sub["target"], reason=too_big)
            return
        self._apply(sub, op, plan, failure)

    @staticmethod
    def _out_of_scope(plan: Plan) -> str | None:
        files = {e["path"] for e in plan.edits}
        changed = sum(max(e["old"].count("\n"), e["new"].count("\n")) + 1 for e in plan.edits)
        if len(files) > MAX_DELIBERATION_FILES:
            return f"proposed change touches {len(files)} files (limit {MAX_DELIBERATION_FILES})"
        if changed > MAX_DELIBERATION_CHANGED_LINES:
            return f"proposed change spans {changed} lines (limit {MAX_DELIBERATION_CHANGED_LINES})"
        return None

    def _apply(self, sub: dict, op, plan: Plan, failure: dict) -> None:
        tests = self.state["world"]["tests"]
        records = []
        for e in plan.edits:
            r = self.reflex("fs.replace_text", WRITE_WORKSPACE, path=e["path"], old=e["old"], new=e["new"])
            if not r.ok:
                for rec in reversed(records):
                    self.reflex("fs.restore", WRITE_WORKSPACE, write_record=rec)
                tests["fresh"] = False if records else tests["fresh"]
                if records:
                    self.state["pending_prediction"] = {"kind": "rollback", "expected_passed": tests["passed"],
                                                        "expected_failed": sorted(tests["failed"])}
                sub["rejected_plans"].append([op.name, _fp(plan.edits)])
                self._record_attempt(sub, op, plan, "edit_refused", prediction_error=None, note=r.error)
                return
            records.append(r.data["write"])
        edit_id = f"e{len(self.state['world']['edits']) + 1}"
        self.state["world"]["edits"].append({"edit_id": edit_id, "subgoal": sub["id"], "operator": op.name,
                                             "rationale": plan.rationale, "write_records": records, "kept": True})
        tests["fresh"] = False
        prediction = {"kind": "edit", "edit_id": edit_id, "subgoal": sub["id"], "operator": op.name,
                      "target": sub["target"], "target_expected": "passed",
                      "preserve_passing": list(tests["passed"]),
                      "signature_before": sub["signature"], "context_hash_before": sub["context_hash"],
                      "edits": plan.edits, "rationale": plan.rationale, "llm": plan.llm}
        self.state["pending_prediction"] = prediction
        self._record_attempt(sub, op, plan, "pending", prediction_error=None, note=plan.rationale)
        self.trace("prediction", edit_id=edit_id, subgoal=sub["id"], target=sub["target"], expect="target passes",
                   preserve_passing=len(prediction["preserve_passing"]),
                   stated_confidence=(plan.llm or {}).get("confidence"))

    def _record_attempt(self, sub, op, plan, outcome, prediction_error, note) -> None:
        sub["attempts"].append({"operator": op.name, "tier": TIER_NAMES[op.tier], "step": self.state["step"],
                                "outcome": outcome, "prediction_error": prediction_error, "note": note,
                                "stated_confidence": (plan.llm or {}).get("confidence") if plan else None})
        if outcome != "pending":
            self.memory.update_operator(op.name, sub["signature"]["class"], outcome)
            self.trace("attempt_closed", subgoal=sub["id"], operator=op.name, outcome=outcome, note=note)

    # ---- evaluation --------------------------------------------------------------------
    def _evaluate_edit(self, p: dict) -> None:
        tests = self.state["world"]["tests"]
        sub = self._subgoal(p["subgoal"])
        passed = set(tests["passed"])
        failures = self._failures()
        regressions = sorted(t for t in p["preserve_passing"] if t not in passed)
        target_ok = p["target"] in passed
        if not target_ok and p["target"] in failures:
            changed = signature(failures[p["target"]])["key"] != p["signature_before"]["key"]
        else:
            changed = not target_ok
        if regressions:
            outcome = "regressed"
        elif target_ok:
            outcome = "fixed"
        elif changed:
            outcome = "progressed"
        else:
            outcome = "no_effect"
        target_error = 0.0 if target_ok else (0.5 if changed else 1.0)
        error = max(target_error, 1.0 if regressions else 0.0)
        attempt = next(a for a in reversed(sub["attempts"]) if a["outcome"] == "pending")
        attempt.update(outcome=outcome, prediction_error=error, regressions=regressions)
        next(e for e in self.state["world"]["edits"] if e["edit_id"] == p["edit_id"])["outcome"] = outcome
        op_name = p["operator"]
        self.memory.update_operator(op_name, p["signature_before"]["class"], outcome)
        self.trace("evaluation", evaluation_of="edit", edit_id=p["edit_id"], subgoal=sub["id"], outcome=outcome, prediction_error=error,
                   regressions=regressions, stated_confidence=(p["llm"] or {}).get("confidence"))
        # Surprise draws attention: a subgoal whose attempts keep missing becomes more salient.
        sub["salience"] = round(min(1.0, sub["salience"] * (1 + 0.25 * error)), 4)
        if outcome in ("fixed", "progressed"):
            if outcome == "fixed":
                sub["status"] = "resolved"
                sub["resolution"] = f"fixed by {op_name} ({p['edit_id']})"
                self.trace("subgoal_resolved", subgoal=sub["id"], target=sub["target"], resolution=sub["resolution"])
            self.memory.record_episode({
                "task_id": self.state["task_id"], "subgoal": sub["id"], "target": sub["target"],
                "signature_key": p["signature_before"]["key"], "signature": p["signature_before"],
                "context_hash": p["context_hash_before"], "operator": op_name, "outcome": outcome,
                "verified": outcome == "fixed", "edits": p["edits"], "rationale": p["rationale"],
                "llm_used": p["llm"] is not None})
            self.attempt_closed_trace(sub, op_name, outcome)
            return
        edit = next(e for e in self.state["world"]["edits"] if e["edit_id"] == p["edit_id"])
        for rec in reversed(edit["write_records"]):
            self.reflex("fs.restore", WRITE_WORKSPACE, write_record=rec)
        edit["kept"] = False
        self.state["counters"]["rollbacks"] += 1
        sub["rejected_plans"].append([op_name, _fp(p["edits"])])
        if regressions:
            self.goal["unresolved_questions"].append(
                f"Why did {op_name}'s edit for {sub['target']} break {', '.join(regressions[:3])}?")
        self.trace("rollback", edit_id=p["edit_id"], subgoal=sub["id"], reason=outcome)
        self.attempt_closed_trace(sub, op_name, outcome)
        self.state["pending_prediction"] = {"kind": "rollback", "expected_passed": p["preserve_passing"],
                                            "expected_failed": None}
        tests["fresh"] = False

    def attempt_closed_trace(self, sub, op_name, outcome) -> None:
        self.trace("attempt_closed", subgoal=sub["id"], operator=op_name, outcome=outcome, note=None)

    def _evaluate_rollback(self, p: dict) -> None:
        passed = set(self.state["world"]["tests"]["passed"])
        missing = sorted(set(p["expected_passed"]) - passed)
        self.trace("evaluation", evaluation_of="rollback", restored=not missing, missing=missing)
        if missing:
            self._block(f"rollback did not restore the previous state: {missing[:5]} no longer pass")

    # ---- deliberation ------------------------------------------------------------------
    def _implicated_files(self, failure: dict) -> dict[str, list[int]]:
        """Workspace files a failure implicates, with lines of interest.

        Traceback frames first. Then cheap evidence, all through reflexes: the workspace modules
        imported by the files in the traceback, and the definitions of the names the innermost
        frame calls (top-level functions, or methods when the name is defined once). An
        assertion in a test names no frame in the code under test, so without this step the
        projection would not show the bug (E2: the model then invented source text).
        """
        files: dict[str, list[int]] = {}
        frames = [f for f in failure.get("frames") or [] if f.get("path")]
        for f in frames:
            files.setdefault(f["path"], []).append(f["line"])
        for path in list(files):
            for mod in self._imported_workspace_modules(path):
                files.setdefault(mod, [1])
        if frames:
            called = self.reflex("py.called_names", READ_ONLY, path=frames[-1]["path"], line=frames[-1]["line"])
            for name in (called.data["names"] if called.ok else []):
                d = self.reflex("py.definitions", READ_ONLY, name=name)
                defs = d.data["definitions"] if d.ok else []
                tops = [h for h in defs if h["top_level"]]
                pick = tops if len(tops) == 1 else (defs if len(defs) == 1 else [])
                for h in pick:                  # ambiguous names would need type resolution; skip them
                    files.setdefault(h["path"], []).append(h["line"])
        return dict(sorted(files.items())[:MAX_PROJECTION_FILES]) if len(files) > MAX_PROJECTION_FILES else files

    def _imported_workspace_modules(self, path: str) -> list[str]:
        try:
            tree = ast.parse(self.ws.read_text(path))
        except Exception:  # unreadable or unparsable: no import evidence from it
            return []
        mods = set()
        for node in tree.body:
            names = [node.module] if isinstance(node, ast.ImportFrom) and node.module and not node.level else \
                [a.name for a in node.names] if isinstance(node, ast.Import) else []
            for m in names:
                for rel in (m.replace(".", "/") + ".py", m.replace(".", "/") + "/__init__.py"):
                    try:
                        if self.ws.resolve(rel).is_file():
                            mods.add(rel)
                            break
                    except Exception:
                        pass
        return sorted(mods)

    def _projection(self, sub: dict, failure: dict) -> dict:
        files = []
        for path, lines in sorted(self._implicated_files(failure).items()):
            span = self.reflex("fs.read_span", READ_ONLY, path=path, start_line=1, end_line=PROJECTION_FILE_LINES)
            if not span.ok:
                continue
            if span.data["n_lines_total"] > PROJECTION_FILE_LINES:
                span = self.reflex("fs.read_span", READ_ONLY, path=path, start_line=min(lines) - 20, end_line=max(lines) + 20)
            files.append({"path": path, "editable": not self.ws.is_protected(path),
                          "start_line": span.data["start_line"], "end_line": span.data["end_line"],
                          "text": span.data["text"]})
        rejected = [{"operator": a["operator"], "outcome": a["outcome"], "note": a["note"],
                     "regressions": a.get("regressions", [])} for a in sub["attempts"] if a["outcome"] != "pending"]
        return {
            "task": "Make the failing test pass without breaking any passing test.",
            "constraints": ["Edit only files marked editable.", "Each edit replaces text that occurs exactly once.",
                            "Do not delete files.", "Do not change tests to make them pass."],
            "failing_test": {"nodeid": failure["nodeid"], "exc_type": failure.get("exc_type"),
                             "exc_message": failure.get("exc_message"),
                             "traceback_tail": (failure.get("longrepr") or "").replace(str(self.ws.root), "<workspace>")[-2500:]},
            "files": files,
            "previous_attempts": rejected,
            "n_passing_tests": len(self.state["world"]["tests"]["passed"]),
        }

    def _deliberate(self, sub: dict, failure: dict):
        projection = self._projection(sub, failure)
        if not any(f["editable"] for f in projection["files"]):
            # Asking for edits to code the model cannot see buys invented source text (E2).
            return "no_evidence"
        req = DeliberationRequest("propose_patch", projection, PATCH_SCHEMA)
        self.state["counters"]["deliberations"] += 1
        self.trace("deliberation_request", subgoal=sub["id"], deliberator=self.deliberator.name,
                   fingerprint=req.fingerprint(), projection_bytes=len(json.dumps(req.projection)))
        resp = self.deliberator.deliberate(req)
        self.state["counters"]["actions"] += 1
        self.trace("deliberation_response", subgoal=sub["id"], ok=resp.ok, error=resp.error, model=resp.model,
                   uses_llm=True, tier="deliberation", **resp.usage(),
                   confidence=(resp.content or {}).get("confidence") if isinstance(resp.content, dict) else None)
        if not resp.ok:
            return "llm_error"
        if isinstance(resp.content, dict) and resp.content.get("edits") == []:
            self.trace("deliberation_abstained", subgoal=sub["id"], diagnosis=str(resp.content.get("diagnosis"))[:300])
            return "model_abstained"
        problem = validate_patch(resp.content)
        if problem:
            self.trace("deliberation_rejected", subgoal=sub["id"], reason=problem)
            return "invalid_response"
        c = resp.content
        return Plan(c["edits"], c["diagnosis"], {"deliberator": resp.deliberator},
                    llm={"confidence": c["confidence"], "fingerprint": req.fingerprint(), **resp.usage()})
