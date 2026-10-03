"""The executive loop end to end, on tiny repositories built in tmp_path."""
import json

from executive import demo_tasks as T
from executive import metrics
from executive.loop import Executive


def run(dirs, build, deliberator=None, **kw):
    repo, state, memory = dirs
    build(repo)
    ex = Executive(repo, state, memory, deliberator=deliberator, **kw)
    ex.run()
    return ex, metrics.compute(state)


def events(state_dir, kind=None):
    rows = [json.loads(l) for l in (state_dir / "trace.jsonl").read_text().splitlines()]
    return [r for r in rows if kind is None or r["kind"] == kind]


def test_already_passing_suite_completes_after_one_observation(dirs):
    ex, m = run(dirs, T.task_passing)
    assert m["completed_verified"] and m["llm_calls"] == 0
    assert m["actions_total"] == 1 and m["steps"] == 2   # observe, then complete


def test_typo_is_fixed_by_a_skill_without_a_model(dirs):
    llm = T.good_model()
    ex, m = run(dirs, T.task_typo, deliberator=llm)
    assert m["completed_verified"], m
    assert m["llm_calls"] == 0 and llm.calls == []
    assert "return total / len(xs)" in (dirs[0] / "calc" / "stats.py").read_text()
    assert m["subgoals_resolved_without_llm"] == 1
    attempts = ex.goal["subgoals"][0]["attempts"]
    assert [(a["operator"], a["outcome"]) for a in attempts] == [("fix_name_typo", "fixed")]


def test_missing_import_is_added_by_a_skill(dirs):
    ex, m = run(dirs, T.task_missing_import, deliberator=T.good_model())
    assert m["completed_verified"] and m["llm_calls"] == 0, m
    assert (dirs[0] / "calc" / "report.py").read_text().startswith("from calc.stats import mean\n")


def test_logic_bug_escalates_once_at_the_impasse_and_is_verified(dirs):
    llm = T.good_model()
    ex, m = run(dirs, T.task_logic_bug, deliberator=llm)
    assert m["completed_verified"], m
    assert m["llm_calls"] == 1 and len(llm.calls) == 1
    # the model was called only after the cheaper operators were found not to apply
    impasse = events(dirs[1], "impasse")
    assert len(impasse) == 1 and impasse[0]["deliberation_available"]
    decision = [e for e in events(dirs[1], "decision") if e["decision"] == "attempt"][0]
    assert decision["operator"] == "deliberate_patch"
    assert {c["operator"]: c["ok"] for c in decision["candidates"]} == {
        "recall_verified_fix": False, "fix_name_typo": False, "add_missing_import": False, "deliberate_patch": True}
    # projection is bounded and shows only workspace files the failure implicates
    paths = [f["path"] for f in llm.calls[0].projection["files"]]
    assert paths == ["calc/stats.py", "tests/test_stats.py"]
    assert [f["editable"] for f in llm.calls[0].projection["files"]] == [True, False]


def test_regressing_patch_is_rolled_back_and_the_second_attempt_recovers(dirs):
    ex, m = run(dirs, T.task_logic_bug, deliberator=T.wrong_then_right_model())
    assert m["completed_verified"], m
    assert m["llm_calls"] == 2 and m["rollbacks"] == 1 and m["recoveries"] == 1
    assert m["attempts_by_outcome"] == {"fixed": 1, "regressed": 1}
    assert m["false_confidence"] == 1        # 0.85 stated, and it regressed
    ev = events(dirs[1], "evaluation")
    assert [e.get("outcome", "restored" if e.get("restored") else "not_restored") for e in ev] == \
        ["regressed", "restored", "fixed"]
    assert ev[0]["regressions"] == ["tests/test_stats.py::test_median_odd"] and ev[0]["prediction_error"] == 1.0
    assert ex.goal["unresolved_questions"]
    # the regression was observed only between the edit and its rollback: no subgoal for it
    assert [s["target"] for s in ex.goal["subgoals"]] == ["tests/test_stats.py::test_median_even"]
    assert m["subgoals_resolved_without_llm"] == 0


def test_model_editing_a_test_is_refused_structurally(dirs):
    ex, m = run(dirs, T.task_logic_bug, deliberator=T.test_editing_model())
    assert (dirs[0] / "tests" / "test_stats.py").read_text() == T.TESTS
    assert m["status"] == "blocked" and m["attempts_by_outcome"] == {"edit_refused": 2}
    assert m["human_interventions_needed"] == 1


def test_malformed_model_output_is_rejected_not_applied(dirs):
    ex, m = run(dirs, T.task_logic_bug, deliberator=T.malformed_model())
    assert m["status"] == "blocked" and m["attempts_by_outcome"] == {"invalid_response": 2}
    assert "s[mid + 1]" in (dirs[0] / "calc" / "stats.py").read_text()


def test_impasse_without_a_deliberator_blocks_and_leaves_no_edits(dirs):
    ex, m = run(dirs, T.task_logic_bug)
    assert m["status"] == "blocked" and "impasse" in m["blocked_reason"]
    assert ex.goal["subgoals"][0]["status"] == "abandoned"
    assert (dirs[0] / "calc" / "stats.py").read_text() == T.STATS.replace(
        "return (s[mid - 1] + s[mid]) / 2", "return (s[mid] + s[mid + 1]) / 2")


def test_no_tests_collected_blocks_rather_than_claiming_success(dirs):
    ex, m = run(dirs, T.task_no_tests)
    assert m["status"] == "blocked" and "no tests" in m["blocked_reason"]


def test_memory_turns_a_model_dependent_fix_into_a_model_free_one(tmp_path):
    memory = tmp_path / "memory"
    first = (tmp_path / "r1", tmp_path / "s1", memory)
    second = (tmp_path / "r2", tmp_path / "s2", memory)
    for d in (first[0], second[0]):
        d.mkdir()
    _, m1 = run(first, T.task_logic_bug, deliberator=T.good_model())
    llm = T.good_model()
    ex2, m2 = run(second, T.task_logic_bug, deliberator=llm)
    assert m1["llm_calls"] == 1 and m2["llm_calls"] == 0 and llm.calls == []
    assert m2["completed_verified"]
    assert [a["operator"] for a in ex2.goal["subgoals"][0]["attempts"]] == ["recall_verified_fix"]


def test_resume_after_interruption_continues_from_persisted_state(dirs):
    repo, state, memory = dirs
    T.task_typo(repo)
    Executive(repo, state, memory, max_steps=2).run()        # observe + apply, then the budget stops it
    s = json.loads((state / "state.json").read_text())
    assert s["status"] == "blocked" and s["pending_prediction"]["operator"] == "fix_name_typo"
    s["status"], s["blocked_reason"], s["goals"][0]["status"] = "active", None, "active"
    (state / "state.json").write_text(json.dumps(s))      # the human grants more budget
    ex = Executive(repo, state, memory, max_steps=10)
    ex.run()
    assert ex.state["status"] == "complete"
    assert events(state, "task_resumed") and events(state, "evaluation")[0]["outcome"] == "fixed"


def test_identical_inputs_give_identical_decisions(tmp_path):
    def decisions(i):
        d = (tmp_path / f"r{i}", tmp_path / f"s{i}", tmp_path / f"m{i}")
        d[0].mkdir()
        run(d, T.task_logic_bug, deliberator=T.wrong_then_right_model(), task_id="same")
        keep = ("decision", "operator", "outcome", "reason", "kind", "capability", "regressions", "fingerprint")
        return [{k: e[k] for k in keep if k in e} for e in events(d[1])]
    assert decisions(1) == decisions(2)


def test_oversized_model_change_is_handed_off_not_applied(dirs):
    repo = dirs[0]
    ex, m = run(dirs, T.task_logic_bug, deliberator=T.sprawling_model())
    assert m["status"] == "blocked" and m["attempts_by_outcome"] == {"out_of_scope": 1}
    assert events(dirs[1], "handoff")[0]["reason"].startswith("proposed change spans")
    assert "s[mid + 1]" in (repo / "calc" / "stats.py").read_text()   # untouched


def test_failure_in_a_method_shows_the_model_the_method(dirs):
    llm = T.method_fix_model()
    ex, m = run(dirs, T.task_method_bug, deliberator=llm)
    assert m["completed_verified"] and m["llm_calls"] == 1, m


def test_model_abstention_hands_off_without_retrying(dirs):
    llm = T.abstaining_model()
    ex, m = run(dirs, T.task_logic_bug, deliberator=llm)
    assert m["status"] == "blocked" and len(llm.calls) == 1
    assert m["attempts_by_outcome"] == {"model_abstained": 1}
    assert events(dirs[1], "handoff")[0]["reason"] == "model_abstained"


def test_no_editable_evidence_means_no_model_call(dirs):
    repo = dirs[0]
    T._write(repo, {"conftest.py": "", "tests/test_only.py": "def test_x():\n    assert 1 == 2\n"})
    llm = T.good_model()
    ex = Executive(repo, dirs[1], dirs[2], deliberator=llm)
    ex.run()
    assert llm.calls == [] and ex.state["status"] == "blocked"
    assert [a["outcome"] for a in ex.goal["subgoals"][0]["attempts"]] == ["no_evidence"]
